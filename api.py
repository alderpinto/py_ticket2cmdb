from flask import Flask, request, jsonify
from main import collect_ticket_ids, process_ticket_ids

app = Flask(__name__)

@app.route('/collect-tickets', methods=['POST'])
def trigger_collect_ticket_ids():
    try:
        # Verifica se a requisição é do tipo POST e se contém um arquivo de texto
        if 'file' not in request.files:
            # Obtém os dados da requisição
            request_data = request.get_json()
            # Acessar os dados da requisição
            ticketcreatetime_ini = request_data.get('ticketcreatetime_ini')
            ticketcreatetime_end = request_data.get('ticketcreatetime_end')    
            auth_to_export = request_data.get('auth_to_export')    
            user_auth_to_import = request_data.get('user_auth_to_import')    
            pass_auth_to_import = request_data.get('pass_auth_to_import')    
            endpoint_url_export = request_data.get('endpoint_url_export')    
            endpoint_url_import = request_data.get('endpoint_url_import')    
            class_to_import = request_data.get('class_to_import')
            limit = request_data.get('limit')
            #routeget, authget, dtini, dtend, userauthput, pswauthput, routeput, classimp
            task = collect_ticket_ids.delay(endpoint_url_export, 
                                auth_to_export, 
                                ticketcreatetime_ini, 
                                ticketcreatetime_end, 
                                user_auth_to_import, 
                                pass_auth_to_import, 
                                endpoint_url_import, 
                                class_to_import,
                                limit)
            # Obter o ID da tarefa
            task_id = task.id
            return f'Collecting ticket IDS without sending file... Task ID: {task_id}', 200
        else:
            file = request.files['file']
            if file.filename == '':
                return jsonify({'error': 'Nome do arquivo não está definido.'}), 400            

            # Acessar os dados da requisição   
            auth_to_export = request.form.get('auth_to_export')    
            user_auth_to_import = request.form.get('user_auth_to_import')    
            pass_auth_to_import = request.form.get('pass_auth_to_import')    
            endpoint_url_export = request.form.get('endpoint_url_export')    
            endpoint_url_import = request.form.get('endpoint_url_import')    
            class_to_import = request.form.get('class_to_import')         

            # Lê o arquivo e extrai os IDs
            ids = []
            for line in file:
                # Assumindo que o arquivo possui uma ID por linha
                ids.append(line.strip().decode('utf-8'))

            task = process_ticket_ids.delay(ids,
                                     endpoint_url_export,
                                     auth_to_export,
                                     user_auth_to_import,
                                     pass_auth_to_import,
                                     endpoint_url_import,
                                     class_to_import)
            # Obter o ID da tarefa
            task_id = task.id
            #return jsonify({'results': results}), 200
            return f'Collecting ticket IDs... Task ID: {task_id}', 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=True)