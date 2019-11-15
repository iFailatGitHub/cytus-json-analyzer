import pandas as pd
import xlsxwriter as xw
import xlsxwriter.worksheet as xws

class ExcelWriter:
    df: pd.DataFrame
    writer: pd.ExcelWriter
    workbook: xw.Workbook
    sheet: xws.Worksheet

    def __init__(self, df: pd.DataFrame, path: str):
        self.df = df
        self.writer = pd.ExcelWriter(path, engine="xlsxwriter") # pylint: disable=abstract-class-instantiated
        df.to_excel(self.writer, sheet_name="Chart Stats", header=False)

        self.workbook = self.writer.book
        self.sheet = self.writer.sheets["Chart Stats"]

    def format_table(self):
        format_decimal_word = ["per_sec", "base", "bpm", "length", "level"]
        decimal_format = self.workbook.add_format({"num_format": "0.00"})
        rate_format = self.workbook.add_format({"num_format": "#0.00%"})
        score_format = self.workbook.add_format({"num_format": "#,###"})

        do_not_avg_cols = ["chart_id", "title", "artist",
                           "illustrator", "charter", "diff"]
        col_formats = []
        cols = self.df.columns.values.tolist()
        cols.insert(0, self.df.index.name)

        for idx, header in enumerate(cols):
            col_header = dict()
            col_header["header"] = self._format_header_name(header)
            if header not in do_not_avg_cols:
                col_header["total_function"] = "average"
            elif header == "chart_id":
                col_header["total_string"] = "Average"

            if any([header.endswith(word) for word in format_decimal_word]):
                self.sheet.set_column(idx, idx, cell_format=decimal_format)
            elif header.endswith("rate") or header.endswith("tp"):
                self.sheet.set_column(idx, idx, cell_format=rate_format)
            elif header.endswith("score"):
                self.sheet.set_column(idx, idx, cell_format=score_format)

            col_formats.append(col_header)

        table_opts = {
            "first_column": True,
            "style": "Table Style Medium 6",
            "name": "ChartStats",
            "total_row": True,
            "columns": col_formats,
        }
        self.sheet.add_table(0, 0, len(self.df.index), len(cols) - 1, table_opts)

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
