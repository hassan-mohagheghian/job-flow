"""Opportunities infrastructure — lazy imports to avoid circular dependencies."""


def __getattr__(name: str):
    _exports = {
        "OpportunityModel": ("opportunities.infrastructure.models.opportunity_model", "OpportunityModel"),
        "OpportunityEvaluationModel": ("opportunities.infrastructure.models.opportunity_model", "OpportunityEvaluationModel"),
        "OpportunityNoteModel": ("opportunities.infrastructure.models.opportunity_model", "OpportunityNoteModel"),
        "OpportunityLinkModel": ("opportunities.infrastructure.models.opportunity_model", "OpportunityLinkModel"),
        "SQLAlchemyOpportunityRepository": ("opportunities.infrastructure.repositories.sa_opportunity_repository", "SQLAlchemyOpportunityRepository"),
        "SQLAlchemyOpportunityEvaluationRepository": ("opportunities.infrastructure.repositories.sa_opportunity_repository", "SQLAlchemyOpportunityEvaluationRepository"),
        "SQLAlchemyOpportunityNoteRepository": ("opportunities.infrastructure.repositories.sa_opportunity_repository", "SQLAlchemyOpportunityNoteRepository"),
        "SQLAlchemyOpportunityLinkRepository": ("opportunities.infrastructure.repositories.sa_opportunity_repository", "SQLAlchemyOpportunityLinkRepository"),
    }
    if name in _exports:
        module_path, attr = _exports[name]
        import importlib
        mod = importlib.import_module(module_path)
        return getattr(mod, attr)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "OpportunityModel",
    "OpportunityEvaluationModel",
    "OpportunityNoteModel",
    "OpportunityLinkModel",
    "SQLAlchemyOpportunityRepository",
    "SQLAlchemyOpportunityEvaluationRepository",
    "SQLAlchemyOpportunityNoteRepository",
    "SQLAlchemyOpportunityLinkRepository",
]
