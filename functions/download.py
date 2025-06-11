def converter_para_download(df):
    return df.to_excel(index=False, engine='openpyxl')