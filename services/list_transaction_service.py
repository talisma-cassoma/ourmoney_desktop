from entities.transactions_entity import TransactionEntity
from repositories.transactions_repository import TransactionsRepository
from utils.logger import get_logger
from services.import_json_service import import_transactions_from_json

class ListTransactions:
    def __init__(self):
        self._transactions: list[TransactionEntity] = []
        self._repository = TransactionsRepository()  # Convenção para atributo protegido
        self._logger = get_logger("ListTransactionsOnDemande")
        #if empty import transactions from json()
        import_transactions_from_json()
        
    def fetch_all(self)-> list[TransactionEntity]:
        return self._repository.get_all()
        
    def fetch(self, last_date=None, filters=None) -> list[TransactionEntity]:
        if filters is None:
            filters = {
                "keyword": "",
                "category": [],
                "type": [],
                "status": [],
                "start_date": "",
                "end_date": ""
            }


        # Se todos os filtros estiverem vazios, buscar por data
        is_empty = (
            filters["keyword"] == None and
            filters["category"] == None and
            filters["type"] == None and
            filters["status"] == None and
            filters["start_date"] == None and
            filters["end_date"] == None
        )

        #print(f"filters: {filters}")
        
        if is_empty:
            transactions = self._repository.fetch_somes(last_date)
            self.total()
            return transactions

        transactions = self._repository.search_transactions_by_filters(last_date=last_date, filters=filters)
        return transactions

    def  fetch_deleted(self)-> list[TransactionEntity]:
        return self._repository.get_deleted_transactions()
    
    def fetch_updated(self)-> list[TransactionEntity]:
        return self._repository.get_updated_transactions()
    
    def fetch_unsynced(self)-> list[TransactionEntity]:
        return self._repository.get_unsynced_transactions()
    
    def total(self, filters=None):
        if filters is None:
            return self._repository.get_total()
        return self._repository.get_total(filters)
    