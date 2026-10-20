#Errors the Controller raises


class PlannerError(Exception):
    status = 400

    def __init__(self, code, field, message, detail=""):
        super().__init__(message)
        self.code = code
        self.field = field
        self.message = message
        self.detail = detail

    def to_dict(self):
        return {"error": {"code": self.code, "field": self.field,
                          "message": self.message, "detail": self.detail}}


class ValidationError(PlannerError):    # ER1-ER6, ER8: nothing was changed
    status = 422


class NotFoundError(PlannerError):      # ER7: event or task no longer exists
    status = 404


class SlotTakenError(PlannerError):     # test T9: slot no longer free
    status = 409