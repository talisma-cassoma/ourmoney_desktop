import logging
import requests
import json

from convertTimeFormat import convert_to_iso8601
from datetime import datetime
from model import Model
from exportJson import export_transactions_to_json
from exportCsv import export_transactions_to_csv
from exportXlsx import export_transactions_to_excel



# Configuração do logging
logging.basicConfig(filename='app.log', level=logging.INFO, format='%(asctime)s %(levelname)s:%(message)s')

class Controller:
    def __init__(self, main_window=None):
        self.main_window = main_window
        self.model = Model()
        #self.api_url = "https://our-money-bkd.onrender.com"
        self.api_url = "http://localhost:3000"
        self.timeout = 10

    def is_online(self):
        """Checa se a máquina está conectada ao servidor."""
        try:
            response = requests.get(f"{self.api_url}/api/ping", timeout=self.timeout)
            if response.status_code == 200:
                return True
        except (requests.ConnectionError, requests.Timeout):
            return False

    def get_all_transactions(self):
        return self.model.get_all_transactions()
    
    def fetch_transactions(self, last_date=None):
        return self.model.fetch_transactions(last_date)
    
    def insert_transaction(self, description, 
                           type, category, price, 
                           owner='talisma', 
                           email='talisma@email.com', 
                           status='unsynced'):
        self.model.insert_one(description, type, category, price, owner, email, status)

    def delete_transaction(self, transaction_id):
        self.model.delete(transaction_id)

    def get_total_of_transactions(self):
         total_income, total_outcome = self.model.get_total()
         return total_income, total_outcome
    
    def insert_many(self, transactions):
        self.model.insert_many(transactions)

    
    def refresh_transaction_view(self):
        """Atualiza a exibição das transações na GUI."""
        self.transactions_list.clear()  # Limpa a lista atual
        transactions = self.get_all_transactions()  # Método para obter todas as transações do DB
        for transaction in transactions:
            self.transactions_list.addItem(f"{transaction['description']} - {transaction['price']} - {transaction['createdAt']}")

    def synchronize_data(self):
        """Baixa dados do servidor para o SQLite local e sincroniza as transações baixadas."""
        if not self.is_online():
            logging.info("Sem conexão. Dados não puxados.")
            return None

        try:
            response = requests.get(f"{self.api_url}/api/transactions/unsynced", timeout=self.timeout)
            if response.status_code == 200:
                data = response.json()
                self.store_in_local_db(data)
                self.push_local_transactions()
                return data
            else:
                logging.error(f"Erro na resposta do servidor: {response.status_code}")
                return None
        except Exception as e:
            logging.error(f"Erro ao puxar dados: {e}")
            return None

    def upadate_status(self, transactions):
        """Atualiza o status de 'synced' das transações baixadas no servidor."""
        for transaction in transactions:
            try:
                response = requests.patch(
                    f"{self.api_url}/api/transactions/{transaction['id']}",
                    json={'status': 'synced'},
                    timeout=self.timeout
                )
                if response.status_code == 200:
                    logging.info(f"Transação {transaction['id']} marcada como sincronizada no servidor.")
                else:
                    logging.error(f"Erro ao marcar transação {transaction['id']} como sincronizada: {response.status_code}")
            except Exception as e:
                logging.error(f"Erro ao atualizar status de sincronização no servidor para a transação {transaction['id']}: {e}")

    def push_local_transactions(self):
        """Envia transações locais para o servidor, convertendo o createdAt para o formato ISO 8601 (UTC)."""
        if self.is_online():
            unsynced_transactions = self.model.get_unsynced_transactions()
            
            transactions_to_push = []
            deleted_transactions_ids = []  # To store transactions with status 'deleted'
            updated_transactions = [] 

            for transaction in unsynced_transactions:
                if transaction[8] == 'deleted':
                    deleted_transactions_ids.append(transaction[0])
                if transaction[8] == 'updated':
                   updated_transactions.append(transaction)

                transaction_dict = {
                    "id": transaction[0],
                    "description": transaction[1],
                    "type": transaction[2],
                    "category": transaction[3],
                    "price": transaction[4],
                    "owner": transaction[5],
                    "email": transaction[6],
                    "createdAt": convert_to_iso8601(transaction[7]),
                    "status": "synced" if transaction[8] == "unsynced" else transaction[8]
                }
                transactions_to_push.append(transaction_dict)

            # Sending transactions in chunks
            chunk_size = 100  # Define your chunk size
            for i in range(0, len(transactions_to_push), chunk_size):
                chunk = transactions_to_push[i:i + chunk_size]
                try:
                    response = requests.post(f"{self.api_url}/api/offline/transactions", json=chunk, timeout=self.timeout)
                    if response.status_code == 200:
                        self.model.mark_as_synced(chunk)  # Mark only the successfully sent chunk as synced
                        logging.info(f"{len(chunk)} transações enviadas com sucesso!")
                    else:
                        logging.error(f"Erro ao enviar dados. Status Code: {response.status_code}")
                except Exception as e:
                    logging.error(f"Erro ao enviar transações offline: {e}")
            self.model.update_many(updated_transactions)
            self.model.delete_many(deleted_transactions_ids)
        else:
            logging.info("Sem conexão. Dados não enviados.")
   
    def store_in_local_db(self, data):
        """Armazena as transações baixadas no banco de dados local."""
        for transaction in data:
            createdAt = transaction.get('createdAt')
            if createdAt is not None:
                try: 
                    convertedTime = convert_to_iso8601(createdAt)
                    self.model.insert_non_synced_transaction(
                        transaction['id'],
                        str(transaction['description']).strip().lower(),
                        transaction['type'],
                        str(transaction['category']).strip().lower(),
                        transaction['price'],
                        convertedTime,
                        status='synced'
                    )
                except ValueError as ve:
                    logging.error(f"Erro ao analisar a data: {ve}")
                except KeyError as ke:
                    logging.error(f"Chave ausente na transação: {ke}")
                except Exception as e:
                    logging.error(f"Erro ao inserir a transação: {e}")
                    
    def export_file(self, index):
        # index 0 for json 
        # index 1 for csv
        # index 2 for xlsx
        if index == 0:
            try:
                export_transactions_to_json()
                logging.info("status: success, Transactions saved successfully.")
            except Exception as e:
                logging.error(f"status: error:{ str(e)}")
        if index == 1:
            try:
                export_transactions_to_csv()
                logging.info("status: success, Transactions exported to CSV successfully.")
            except Exception as e:
                logging.error(f"status: error:{ str(e)}")
        if index == 2:
            try:
                export_transactions_to_excel()
                logging.info("status: success, Transactions exported to excel successfully.")
            except Exception as e:
                logging.error(f"status: error:{ str(e)}")
     