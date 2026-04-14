from src.services.search.drug_search_service import DrugSearchService

_drug_search_service_instance = None


def get_drug_search_service():
    global _drug_search_service_instance

    if _drug_search_service_instance is None:
        _drug_search_service_instance = DrugSearchService()

    return _drug_search_service_instance
