import pyodbc
import pandas as pd
import time, json, datetime
import re
import tempfile
import os

def connect_to_mdb(mdb_path):
    return pyodbc.connect(f"DRIVER={{Microsoft Access Driver (*.mdb, *.accdb)}};DBQ={mdb_path};")

# Map months to their respective letters
month_letter_map = {
    4: "A", 5: "B", 6: "C", 7: "D", 8: "E", 9: "F",
    10: "G", 11: "H", 12: "I", 1: "J", 2: "K", 3: "L"
}

# Get the current month's letter
current_month = datetime.datetime.now().month
LETTER = month_letter_map[current_month]

# Define required elements and values
required_data = {
    "element": ["C", "MN", "S", "P", "SI", "CU", "CR", "NI", "AL", "MO", "V", "N", "TI", "FE", "CE"],
    "required": ["(MIN)0.152 TO 0.301(MAX)", "NO NEED", "(MIN)0.10 TO 0.60(MAX)", "(MIN)0.10 TO 0.60(MAX)", "(MIN)0.15 TO 0.30(MAX)",
                 "NO NEED", "(MIN)0.15 TO 0.40(MAX)", "NO NEED", "(MIN)0.010 TO 0.025(MAX)", "NO NEED", "NO NEED", "NO NEED",
                 "NO NEED", "NO NEED", "NO NEED"]
}
required_df = pd.DataFrame(required_data)

def read_mdb_data(conn):
    df_QRData = pd.read_sql("SELECT SeqNo, DispEle, Content FROM QRData", conn)
    df_QRList = pd.read_sql("SELECT SeqNo, SampIndex, AnaDate, AnaTime, Kind FROM QRList", conn)
    
    df_QRList["AnaDate"] = pd.to_datetime(df_QRList["AnaDate"], errors="coerce")
    df_QRList["AnaTime"] = pd.to_datetime(df_QRList["AnaTime"], errors="coerce").dt.time
    df_QRList = df_QRList[df_QRList["Kind"] == "AV"]
    df_QRList = df_QRList[df_QRList['SampIndex'].str.contains('FLP|LLP', case=False, na=False)]
    df_QRList["new_sample_index"] = df_QRList['SampIndex'].str.replace(r'[^a-zA-Z0-9]', '', regex=True)

    return df_QRData, df_QRList

def get_latest_sampleindex(df, pattern):
    df_filtered = df[df["SampIndex"].str.match(pattern, case=False, na=False)]
    if df_filtered.empty:
        return None, None, None, None
    latest_date = df_filtered["AnaDate"].max()
    latest_time = df_filtered[df_filtered["AnaDate"] == latest_date]["AnaTime"].max()
    latest_sampleindex = df_filtered[(df_filtered["AnaDate"] == latest_date) & 
                                     (df_filtered["AnaTime"] == latest_time)]["SampIndex"].iloc[0]

    modified_latest_sample_index = re.sub(r'[^a-zA-Z0-9]', '', latest_sampleindex)
    str_to_filter = re.match(r'^([A-Za-z]*\d+)', modified_latest_sample_index).group(1)

    return latest_date.date(), latest_time, latest_sampleindex, str_to_filter
   
def pivot_content_data(df):
    df_pivot = df.groupby("DispEle")["Content"].apply(list).reset_index()
    
    col_names = []

    for samp in df["SampIndex"].unique():
        # Filter dataframe for this specific SampIndex
        filtered = df[df["SampIndex"] == samp]
        
        if not filtered.empty:
            # Get the first AnaTime (you can choose logic: first, last, max, min, etc.)
            ana_time = str(filtered["AnaTime"].iloc[0])[:5]  # get HH:MM
            
            # Clean the SampIndex
            clean_samp = str(samp).replace("(", "").replace(")", "").strip()

            # Add space before FLP or LLP if not already present
            for target in ["FLP", "LLP"]:
                idx = clean_samp.find(target)
                if idx > 0 and clean_samp[idx - 1] != "-":
                    clean_samp = clean_samp[:idx].strip() + "-" + clean_samp[idx:].strip()

            col_names.append(f"{clean_samp} | {ana_time}")

    df_pivot[col_names] = pd.DataFrame(df_pivot["Content"].tolist(), index=df_pivot.index)
    df_pivot.drop(columns=["Content"], inplace=True)
    df_pivot.rename(columns={"DispEle": "element"}, inplace=True)
    return df_pivot


def main():
    mdb_path = r"C:\PDAWin\Qrt\QResult.mdb"
    #mdb_path = r"C:\Users\Admin\Desktop\Akshay\New folder\QResult.mdb"
    conn = connect_to_mdb(mdb_path)
    prev_k_index, prev_srk_index = None, None
    
    while True:
        try:
            k_falg = False
            srk_flag =False
            df_QRData, df_QRList = read_mdb_data(conn)
            
            # Generate dynamic patterns based on the month
            k_pattern = rf"^\(?{LETTER}[-\s]?\d+.*"
            srk_pattern = rf"^\(?SR\s?{LETTER}[-\s]?\d+.*"
            
            latest_k_date, latest_k_time, latest_K_sampleindex, k_str_to_filter = get_latest_sampleindex(df_QRList, k_pattern)
            latest_srk_date, latest_srk_time, latest_SRK_sampleindex, srk_str_to_filter = get_latest_sampleindex(df_QRList, srk_pattern)


            if latest_K_sampleindex and latest_K_sampleindex != prev_k_index:
                df_k_final = df_QRList[df_QRList["new_sample_index"].str.startswith(k_str_to_filter)].merge(df_QRData, on="SeqNo", how="inner")
                df_k_pivot = pivot_content_data(df_k_final)
                df_k_pivot["element"] = df_k_pivot["element"].str.strip()
                final_k_df = df_k_pivot.merge(required_df, on="element", how="left")
                final_k_df["element"] = pd.Categorical(final_k_df["element"], categories=required_data["element"], ordered=True)
                final_k_df = final_k_df.sort_values("element").reset_index(drop=True)
                if not final_k_df.empty:   
                    for s in range(5):
                        try:
                            final_k_df.to_csv("k_output.csv", index=False, mode="w")
                            k_falg = True
                            break
                        except:
                            continue
                    if k_falg:
                        prev_k_index = latest_K_sampleindex

            if latest_SRK_sampleindex and latest_SRK_sampleindex != prev_srk_index:
                #df_srk_final = df_QRList[df_QRList["new_sample_index"].str.startswith(srk_str_to_filter)].drop("new_sample_index",axis=1).merge(df_QRData, on="SeqNo", how="inner")
                df_srk_final = df_QRList[df_QRList["new_sample_index"].str.startswith(srk_str_to_filter)].drop("new_sample_index", axis=1).merge(df_QRData, on="SeqNo", how="inner")
                df_srk_pivot = pivot_content_data(df_srk_final)
                df_srk_pivot["element"] = df_srk_pivot["element"].str.strip()
                final_srk_df = df_srk_pivot.merge(required_df, on="element", how="left")
                final_srk_df["element"] = pd.Categorical(final_srk_df["element"], categories=required_data["element"], ordered=True)
                final_srk_df = final_srk_df.sort_values("element").reset_index(drop=True)
                if not final_srk_df.empty:   
                    for n in range(5):
                        try:
                            final_srk_df.to_csv("srk_output.csv", index=False, mode="w")
                            srk_flag = True
                            break
                        except:
                            continue
                    if srk_flag:
                        prev_srk_index = latest_SRK_sampleindex

            time.sleep(1)
        except:
            pass
            
      

if __name__ == "__main__":
    main()
