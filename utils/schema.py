from enum import Enum


class WorkStatus(Enum):
    NOT_SUBMITTED = 0
    NOT_SUBMITTED_RED = 1
    CORRECTED = 2
    CORRECTED_GREEN = 3
    DONE_COMMIT = 5
    NOT_COMMIT = 6 # 缺考

    def __str__(self):
        if self == WorkStatus.NOT_SUBMITTED:
            return "未提交"
        elif self == WorkStatus.NOT_SUBMITTED_RED:
            return "[red]未提交[/red]"
        elif self == WorkStatus.CORRECTED:
            return "已批改"
        elif self == WorkStatus.CORRECTED_GREEN:
            return "[green]已批改[/green]"
        elif self == WorkStatus.NOT_COMMIT:
            return "[red]缺考[/red]"
        elif self == WorkStatus.DONE_COMMIT:
            return "已提交"
        else:
            return "未知状态"
