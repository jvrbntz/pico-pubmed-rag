"""Cleans the raw MTSamples dataset: drops unused columns, drops rows missing transcription, and assigns a stable case_id."""


def clean_dataset(df):
    df = (
        df.drop(columns=["keywords"])
        .dropna(subset=["transcription"])
        .rename(columns={"Unnamed: 0": "case_id"})
    )

    return df
