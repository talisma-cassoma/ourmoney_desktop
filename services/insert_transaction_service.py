from entities.transactions_entity import TransactionEntity
from repositories.transactions_repository import TransactionsRepository
from dto.transaction_dto import TransactionDTO
from utils.logger import get_logger
from utils.shared.convertTimeFormat import is_iso8601_format


class InsertTransactionService:
    def __init__(self):
        self._repository = TransactionsRepository()  # Convenção para atributo protegido
        self._logger = get_logger("InsirtTransactionService")

    def one(self, transaction_dto: TransactionDTO):

        transaction = TransactionEntity(
            description=transaction_dto.description,
            type=transaction_dto.type,
            category=transaction_dto.category,
            price=transaction_dto.price,
            created_at= transaction_dto.created_at,
            status=transaction_dto.status
        )
        self._repository.insert_one(transaction)
    
    def many(self, transactions_dto: list[TransactionDTO]):


        transactions_entity = [
            TransactionEntity(
                id=transaction_dto.id,
                description=transaction_dto.description,
                type=transaction_dto.type,
                category=transaction_dto.category,
                price=transaction_dto.price,  # Converter para formato seguro
                created_at= transaction_dto.created_at,
                status= transaction_dto.status 
            )
            for transaction_dto in transactions_dto
        ]

        self._repository.insert_many(transactions_entity)

    
