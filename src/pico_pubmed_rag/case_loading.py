"""Loads one case from the cleaned dataset by case_id."""


def load_case(df, case_id):
    matching_rows = df[df["case_id"] == case_id]
    if matching_rows.empty:
        raise KeyError(f"case_id {case_id} not found")
    return matching_rows.iloc[0].to_dict()
