class Block:
    id: str = ""
    template_name: str = ""

    def get_context(self, request) -> dict:
        return {}

    def has_permission(self, request) -> bool:
        return True
