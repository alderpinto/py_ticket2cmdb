from celery import Celery
from celery.exceptions import MaxRetriesExceededError
from time import sleep
import requests
import redis

# Configuração do Celery
app = Celery('task_queue', broker='redis://redis:6379/0', backend='redis://redis:6379/0')

# Tarefa do Celery para coletar os TicketIDs
@app.task(bind=True, max_retries=3)
def collect_ticket_ids(self, 
                       routeget, 
                       authget, 
                       dtini, 
                       dtend, 
                       userauthput, 
                       pswauthput, 
                       routeput, 
                       classimp,
                       limit):
    try:
        # Coloque o código da tarefa aqui
        url = routeget + 'nph-genericinterface.pl/Webservice/Export/TicketSearch'
        headers = {
            'Content-Type': 'application/json',
            'Authorization': authget,
            'Cookie': 'BIGipServerpool_intranet_otrssti_80=3471122954.20480.0000'
        }
        data = {
            "UserLogin": "root@localhost",
            "Password": "changeme",
            "TicketCreateTimeNewerDate": dtini,
            "TicketCreateTimeOlderDate": dtend,
            "Limit": limit
        }

        response = requests.post(url, headers=headers, json=data)
        print(f"POST request ticket list - Response: {response.status_code}")
        ticket_ids = response.json().get('TicketID', [])

        # Enviar cada TicketID para a próxima tarefa
        for ticket_id in ticket_ids:
            process_ticket_inject.delay(ticket_id, 
                                        routeget, 
                                        authget, 
                                        userauthput, 
                                        pswauthput, 
                                        routeput, 
                                        classimp)

    except (requests.RequestException, ValueError) as exc:
        print(f"Erro ao coletar tickets: {exc}")
        sleep(5)  # Tempo de espera antes de tentar novamente
        try:
            self.retry()
        except MaxRetriesExceededError:
            print("Excedido o número máximo de tentativas")

# Tarefa do Celery para coletar os TicketIDs
@app.task(bind=True, max_retries=3)
def process_ticket_ids(self,
                       ticketids, 
                       routeget, 
                       authget,
                       userauthput, 
                       pswauthput, 
                       routeput, 
                       classimp):
    try:
        ticket_ids = ticketids

        # Enviar cada TicketID para a próxima tarefa
        for ticket_id in ticket_ids:
            process_ticket_inject.delay(ticket_id, 
                                        routeget, 
                                        authget, 
                                        userauthput, 
                                        pswauthput, 
                                        routeput, 
                                        classimp)

    except (requests.RequestException, ValueError) as exc:
        print(f"Erro ao coletar tickets: {exc}")
        sleep(5)  # Tempo de espera antes de tentar novamente
        try:
            self.retry()
        except MaxRetriesExceededError:
            print("Excedido o número máximo de tentativas")  

# Tarefa do Celery para processar os detalhes do Ticket e enviar uma requisição PUT
@app.task
def process_ticket_details(ticket_id, routeget, authget):
    # Coloque o código da tarefa aqui
    url = routeget + 'nph-genericinterface.pl/Webservice/Export/Ticket'
    headers = {
        'Content-Type': 'application/json',
        'Authorization': authget,
        'Cookie': 'BIGipServerpool_intranet_otrssti_80=3471122954.20480.0000'
    }
    data = {
        "UserLogin": "root@localhost",
        "Password": "changeme",
        "TicketID": ticket_id,
        "DynamicFields": "1",
        "Extended": "1",
        "AllArticles": "1"
    }

    response = requests.post(url, headers=headers, json=data)
    print(f"POST request details get for ticket {ticket_id} - Response: {response.status_code}")
    #ticket_details = response.json().get('Ticket', [])
    json_data = response.json()

    # Verificar se a resposta contém a chave "Ticket"
    if "Ticket" in json_data:
        tickets = json_data["Ticket"]

        for ticket in tickets:
            # Verificar se o ticket contém a chave "DynamicField"
            if "DynamicField" in ticket:
                dynamic_fields = ticket["DynamicField"]

                # Renomear a chave "DynamicField" para "dynamicfield_name"
                ticket["DynamicField_Name"] = dynamic_fields
                del ticket["DynamicField"]

                for field in dynamic_fields:
                    # Renomear as chaves "Name" e "Value"
                    field["DynamicField_Name"] = field.pop("Name")
                    field["DynamicField_Value"] = field.pop("Value")
                    
            # Verificar se o ticket contém a chave "DynamicField"
            if "Article" in ticket:
                article_fields = ticket["Article"]

                # Renomear a chave "DynamicField" para "dynamicfield_name"
                ticket["ArticleID"] = article_fields
                del ticket["Article"]                    

    # Transforma o dicionário em uma string JSON com indentação
    return json_data["Ticket"][0]

# Tarefa do Celery para processar os detalhes do Ticket e enviar uma requisição PUT
@app.task(bind=True, max_retries=3)
def process_ticket_inject(self, 
                          ticket_id, 
                          routeget, 
                          authget, 
                          userauthput, 
                          pswauthput, 
                          routeput, 
                          classimp):
    try:
        ticket_details = process_ticket_details(ticket_id, routeget, authget)
        # Modificar o JSON dos detalhes do Ticket e enviar uma requisição PUT
        if ticket_details:
            payload = {
                "UserLogin": userauthput,
                "Password": pswauthput,
                "ConfigItem": {
                    "Number": ticket_id,
                    "Class": classimp,
                    "Name": ticket_details.get('TicketNumber'),
                    "DeplState": "Production",
                    "InciState": "Operational",
                    "CIXMLData": ticket_details # Modificar o JSON conforme necessário
                }
            }

            put_url = routeput + 'nph-genericinterface.pl/Webservice/Import/ConfigItem'
            put_headers = {
                'Content-Type': 'application/json'
            }

            put_response = requests.put(put_url, headers=put_headers, json=payload)
            print(f"PUT request for ticket {ticket_id} - Response: {put_response.status_code}")

    except (requests.RequestException, ValueError) as exc:
        print(f"Erro ao coletar detalhes do ticket: {exc}")
        sleep(5)  # Tempo de espera antes de tentar novamente
        try:
            self.retry()
        except MaxRetriesExceededError:
            print("Excedido o número máximo de tentativas")         

# Iniciar o worker Celery
if __name__ == '__main__':
    app.worker_main(['--loglevel=info'])
