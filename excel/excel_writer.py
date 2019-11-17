import pandas as pd
import xlsxwriter as xw
import xlsxwriter.worksheet as xws

from .formats import FORMATS

NO_AVG_COLS = ["chart_id", "title", "artist", "illustrator", "charter", "diff"]

class ExcelWriter:
    df: pd.DataFrame
    writer: pd.ExcelWriter
    workbook: xw.Workbook
    sheet: xws.Worksheet
    formats: dict()

    def __init__(self, df: pd.DataFrame, path: str):
        self.df = df
        self.writer = pd.ExcelWriter(path, engine="xlsxwriter") # pylint: disable=abstract-class-instantiated
        df.to_excel(self.writer, sheet_name="Chart Stats", header=False, startrow=1)

        self.workbook = self.writer.book
        self.sheet = self.writer.sheets["Chart Stats"]
        self.sheet.freeze_panes(1, 1)

        self.formats = FORMATS

        for format_ in self.formats.values():
            format_["format"] = self.workbook.add_format(format_["format"])
            format_["format"].set_align("vcenter")

        self.default_format = self.workbook.add_format({"align": "vcenter"})

    def format_table(self):
        col_opts_list = []
        cols = self.df.columns.values.tolist()
        cols.insert(0, self.df.index.name)

        for idx, header in enumerate(cols):
            col_opts = dict()
            col_opts["header"] = self._format_header_name(header)

            if header == "chart_id":
                col_opts["total_string"] = "Average"

            if header not in NO_AVG_COLS:
                col_opts["total_function"] = "average"
                col_opts["format"] = self.formats["decimal"]["format"]
            else:
                col_opts["format"] = self.default_format

            for format_ in self.formats.values():
                if any([header.endswith(kw) for kw in format_["keywords"]]):
                    self.sheet.set_column(idx, idx,
                                          cell_format=format_["format"])
                    col_opts["format"] = format_["format"]
                    break
            else:
                self.sheet.set_column(idx, idx, cell_format=self.default_format)

            col_opts_list.append(col_opts)

        table_opts = {
            "first_column": True,
            "style": "Table Style Medium 6",
            "name": "ChartStats",
            "total_row": True,
            "columns": col_opts_list,
        }
        self.sheet.add_table(0, 0, len(self.df.index) + 1, len(cols) - 1,
                             table_opts)

    def close(self):
        self.writer.save()
        self.writer.close()

    @staticmethod
    def _format_header_name(key: str) -> str:
        capitalize_words = ["Bpm", "Fc", "Mm", "Tp", "Id"]
        dot_words = ["Min", "Max", "Sec", "Avg", "Diff"]
        key = key.replace("_", " ")
        key = key.title()
        for word in capitalize_words:
            key = key.replace(word, word.upper())

        for word in dot_words:
            key = key.replace(word, f"{word}.")

        key = key.replace("Cdrag", "C-Drag")
        key = key.replace("Per", "per")

        return key
