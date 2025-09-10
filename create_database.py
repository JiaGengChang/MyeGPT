import pandas as pd
from sqlalchemy import create_engine, text
from tqdm import tqdm

# make sure to run the cloud sql auth proxy in a terminal first
# cloud-sql-proxy --credentials-file ~/Documents/commpass-gpt-8aa313d01ce0.json --port 5432 commpass-gpt:asia-southeast1:commpass-pgsql15
# or add public ip to whitelist in GCP console and connect to database directly

PROJECTDIR="./"

def upload_table_per_patient():
    # Load the data
    df = pd.read_csv(f'{PROJECTDIR}/clindata/MMRF_CoMMpass_IA22_PER_PATIENT.tsv', sep='\t')
    df = df.set_index('PUBLIC_ID')
    print(df.head())

    # Upload to the MySQL database
    with engine.connect() as conn:
        df.to_sql('per_patient', con=conn, if_exists='replace', index=True, index_label='PUBLIC_ID', method='multi')
        print("Data uploaded successfully.")

def upload_table_per_patient_visit():
    # Load the data
    df = pd.read_csv(f'{PROJECTDIR}/clindata/MMRF_CoMMpass_IA22_PER_PATIENT_VISIT.tsv', sep='\t')
    df = df.set_index('PUBLIC_ID')
    print(df.head())

    # Upload to the database
    with engine.connect() as conn:
        df.to_sql('per_visit', con=conn, if_exists='replace', index=True, index_label='PUBLIC_ID')
        print("Data uploaded successfully.")

def upload_table_stand_alone_survival():
    # Load the data
    df = pd.read_csv(f'{PROJECTDIR}/clindata/MMRF_CoMMpass_IA22_STAND_ALONE_SURVIVAL.tsv', sep='\t')
    df = df.set_index('PUBLIC_ID')
    # create a secondary index on 
    print(df.head())

    # Upload to the database
    with engine.connect() as conn:
        df.to_sql('stand_alone_survival', con=conn, if_exists='replace', index=True, index_label='PUBLIC_ID')
        print("Data uploaded successfully.")

def chunker(seq, size):
    # from http://stackoverflow.com/a/434328
    return (seq[pos:pos + size] for pos in range(0, len(seq), size))

def upload_table_salmon_gene_unstranded_counts():
    # Load the data
    df = pd.read_csv(f'{PROJECTDIR}/omicdata/MMRF_CoMMpass_IA22_salmon_geneUnstranded_counts.tsv', sep='\t')
    df = df.set_index('Gene')
    # convert all columns from float to int
    df = df.astype(int)
    # Transpose to have samples as rows and genes as columns
    df = df.transpose()
    df.index.name = 'SAMPLE'
    df = df.reset_index()
    df['PUBLIC_ID'] = df['SAMPLE'].str.extract(r'(MMRF_\d+)')  # Extract the numeric part of the sample name
    df['Visit'] = df['SAMPLE'].str.extract(r'MMRF_\d+_(\d+)_.*$')  # Extract the visit number
    df = df.melt(id_vars=['PUBLIC_ID', 'SAMPLE'], var_name='Gene', value_name='Count')
    # set index
    df.set_index(['PUBLIC_ID','Gene'], inplace=True)

    print(df.head())
    # Upload to the database in chunks to monitor progress better
    with engine.connect() as conn:
        chunksize = int(len(df) / 100) # 1% at a time
        with tqdm(total=len(df)) as pbar:
            for i, cdf in enumerate(chunker(df, chunksize)):
                replace = "replace" if i == 0 else "append"
                cdf.to_sql('salmon_gene_unstranded_counts', con=conn, if_exists=replace, index=True, index_label=['PUBLIC_ID','Gene'])
                pbar.update(chunksize)
        print("Data uploaded successfully.")

def upload_table_salmon_gene_unstranded_tpm():
    # Load the data
    df = pd.read_csv(f'{PROJECTDIR}/omicdata/MMRF_CoMMpass_IA22_salmon_geneUnstranded_tpm.tsv', sep='\t')
    df = df.set_index('Gene')
    # Transpose to have samples as rows and genes as columns
    df = df.transpose()
    df.index.name = 'SAMPLE'
    df = df.reset_index()
    df['PUBLIC_ID'] = df['SAMPLE'].str.extract(r'(MMRF_\d+)')  # Extract the numeric part of the sample name
    df['VISIT'] = df['SAMPLE'].str.extract(r'MMRF_\d+_(\d+)_.*$')  # Extract the visit number
    df = df.melt(id_vars=['PUBLIC_ID', 'SAMPLE'], var_name='Gene', value_name='tpm')
    # set index
    df.set_index(['PUBLIC_ID','Gene'], inplace=True)
    print(df.head())

    # Upload to the database in chunks to monitor progress better

    with engine.connect() as conn:
        # Update 'tpm' values for each (PUBLIC_ID, Gene)
        chunksize = int(len(df) / 100) if len(df) > 100 else len(df)
        with tqdm(total=len(df)) as pbar:
            for i, cdf in enumerate(chunker(df, chunksize)):
                replace = "replace" if i == 0 else "append"
                cdf.to_sql('salmon_gene_unstranded_tpm', con=conn, if_exists=replace, index=True, index_label=['PUBLIC_ID','Gene'])
                pbar.update(chunksize)
        print("TPM values updated successfully.")

# based on Soekojo et al 2022 Genomic Classification of Functional High Risk patients in Multiple myeloma
# add integer-level segment copy number status, defined for segment_mean x as:
# if x <= -1.5 then segment_copy_number_status = -2
# if -1.5 < x <= -0.5 then segment_copy_number_status = -1
# if -0.5 < x <= 0.38 then segment_copy_number_status = 0
# if +0.38 < x <= 0.66 then segment_copy_number_status = +1
# if x > 0.66 then segment_copy_number = +2
def segment_copy_number(x):
    if x <= -1.5:
        return -2
    elif -1.5 < x <= -0.5:
        return -1
    elif -0.5 < x <= 0.38:
        return 0
    elif 0.38 < x <= 0.66:
        return 1
    else:
        return 2

def upload_table_genome_gatk_cna():
    # Load the data
    df = pd.read_csv(f'{PROJECTDIR}/omicdata/Copy Number Estimates-MMRF_CoMMpass_IA22_genome_gatk_cna.seg', sep='\t')
    df['VISIT'] = df['SAMPLE'].str.extract(r'MMRF_\d+_(\d+)_.*$')  # Extract the visit number
    df = df.set_index('SAMPLE')

    df['Segment_Copy_Number_Status'] = df['Segment_Mean'].apply(segment_copy_number)

    print(df.head())
    # Upload to the database
    with engine.connect() as conn:
        df.to_sql('genome_gatk_cna', con=conn, if_exists='replace', index=True, index_label='SAMPLE')
        print("Data uploaded successfully.")

def upload_table_exome_NS_variants():
    # Load the data
    df = pd.read_csv(f'{PROJECTDIR}/omicdata/IGV Downloads-MMRF_CoMMpass_IA22_exome_vcfmerger2_IGV_All_Canonical_NS_Variants.mut', sep='\t', na_values='.')
    df['PUBLIC_ID'] = df['sample'].str.extract(r'(MMRF_\d+)')  # Extract the numeric part of the sample name
    df['VISIT'] = df['sample'].str.extract(r'MMRF_\d+_(\d+)_.*$')  # Extract the visit number
    df = df.set_index(['GENEID','PUBLIC_ID'])
    print(df.head())

    # Upload to the database
    with engine.connect() as conn:
        df.to_sql('exome_ns_variants', con=conn, if_exists='replace', index=True, index_label=['GENEID','PUBLIC_ID'])
        print("Data uploaded successfully.")

def upload_table_stand_alone_trtresp():
    # Load the data
    df = pd.read_csv(f'{PROJECTDIR}/clindata/MMRF_CoMMpass_IA22_STAND_ALONE_TRTRESP.tsv', sep='\t', encoding='latin1')
    df = df.set_index('PUBLIC_ID')
    print(df.head())

    # Upload to the database
    with engine.connect() as conn:
        df.to_sql('stand_alone_trtresp', con=conn, if_exists='replace', index=True, index_label='PUBLIC_ID')
        print("Data uploaded successfully.")

def upload_table_stand_alone_treatment_regimen():
    # Load the data
    df = pd.read_csv(f'{PROJECTDIR}/clindata/MMRF_CoMMpass_IA22_STAND_ALONE_TREATMENT_REGIMEN.tsv', sep='\t', encoding='latin1')
    df = df.set_index('PUBLIC_ID')
    print(df.head())

    # Upload to the database
    with engine.connect() as conn:
        df.to_sql('stand_alone_treatment_regimen', con=conn, if_exists='replace', index=True, index_label='PUBLIC_ID')
        print("Data uploaded successfully.")

def upload_table_gene_annotation():
    # Load the data
    df = pd.read_csv(f'{PROJECTDIR}/refdata/gene_annotation.tsv', sep='\t').rename(columns={'Gene name': 'Gene symbol'})
    df = df.set_index(['Gene stable ID','Gene symbol'])
    print(df.head())

    # Upload to the database
    with engine.connect() as conn:
        df.to_sql('gene_annotation', con=conn, if_exists='replace', index=True, index_label=['Gene stable ID','Gene symbol'])
        print("Data uploaded successfully.")

def upload_table_canonical_ig():
    df = pd.read_csv(f'{PROJECTDIR}/omicdata/SeqFISH Files_MMRF_CoMMpass_IA16a_LongInsert_Canonical_Ig_Translocations.txt', sep='\t')
    df['PUBLIC_ID'] = df['Study_Visit_iD'].str.extract(r'(MMRF_\d+)')  # Extract the numeric part of the sample name
    df = df.sort_values('Study_Visit_iD').groupby('PUBLIC_ID').head(n=1)
    df = df.filter(regex='(_CALL$|^PUBLIC_ID$)')
    df = df.set_index('PUBLIC_ID')

    # upload to the database
    with engine.connect() as conn:
        df.to_sql('canonical_ig', con=conn, if_exists='replace', index=True, index_label='PUBLIC_ID')
        print("Data uploaded successfully.")

def upload_table_wgs_fish():
    df = pd.read_csv(f'{PROJECTDIR}/omicdata/SeqFISH Files_MMRF_CoMMpass_IA22_genome_gatk_cna_seqFISH.tsv', sep='\t')
    df['PUBLIC_ID'] = df['SAMPLE'].str.extract(r'(MMRF_\d+)')  # Extract the numeric part of the sample name
    df['VISIT'] = df['SAMPLE'].str.extract(r'MMRF_\d+_(\d+)_.*$')  # Extract the visit number
    df = df.set_index('PUBLIC_ID')
    df = df.filter(regex='^(?!.*percent$)', axis=1)

    # convert probe values to integer statuses
    _df = df.filter(regex='SeqWGS_Cp_(?!Hyperdiploid)').copy()
    for col in df.filter(regex='SeqWGS_Cp_(?!Hyperdiploid)').columns:
        df[col] = df[col].apply(segment_copy_number)
        _df.rename(columns={col: col.replace('SeqWGS_Cp_', 'SeqWGS_SegmentMean_')}, inplace=True)
    
    # add back probe values
    df = pd.concat([df, _df], axis=1)

    print(df.head())

    # upload to the database
    with engine.connect() as conn:
        df.to_sql('wgs_fish', con=conn, if_exists='replace', index=True, index_label='PUBLIC_ID')
        print("Data uploaded successfully.")

def upload_table_sbs():
    # Load the data
    df = pd.read_csv(f'{PROJECTDIR}/omicdata/SBS86_IA21.tsv', sep='\t')
    df = df.rename(columns={'SAMPLE_ID': 'SAMPLE'})
    df['PUBLIC_ID'] = df['SAMPLE'].str.extract(r'(MMRF_\d+)')
    df['VISIT'] = df['SAMPLE'].str.extract(r'MMRF_\d+_(\d+)_.*$')
    df.columns = df.columns.str.replace('Feature_','')
    df = df.set_index('PUBLIC_ID')
    print(df.head())

    # Upload to the database
    with engine.connect() as conn:
        df.to_sql('mutsig_sbs', con=conn, if_exists='replace', index=True, index_label='PUBLIC_ID')
        print("Data uploaded successfully.")

def upload_table_chromothripsis():
    df = pd.read_csv(f'{PROJECTDIR}/omicdata/chromoth_categorical_df_pval0.05.tsv',sep='\t')
    df = df.set_index('PUBLIC_ID')
    print(df.head())

    # Upload to the database
    with engine.connect() as conn:
        df.to_sql('chromothripsis', con=conn, if_exists='replace', index=True, index_label='PUBLIC_ID')
        print("Data uploaded successfully.")

def upload_table_gep_scores():
    df = pd.read_csv(f'{PROJECTDIR}/omicdata/commpass_gep_risk_scores.csv',sep=',')
    df.columns = df.columns.str.replace('Feature_','')
    df = df.set_index('PUBLIC_ID')
    print(df.head())

    # Upload to the database
    with engine.connect() as conn:
        df.to_sql('gep_scores', con=conn, if_exists='replace', index=True, index_label='PUBLIC_ID')
        print("Data uploaded successfully.")

def upload_table_baf():
    # B-allele frequencies
    # using exome BAF instead of genome BAF as that is too sparse
    df = pd.read_csv(f'{PROJECTDIR}/omicdata/Loss of Heterozygosity Files_MMRF_CoMMpass_IA22_exome_gatk_baf.seg', sep='\t')
    df['PUBLIC_ID'] = df['SAMPLE'].str.extract(r'(MMRF_\d+)')  # Extract the numeric part of the sample name
    df['VISIT'] = df['SAMPLE'].str.extract(r'MMRF_\d+_(\d+)_.*$')  # Extract the visit number
    df = df.set_index('SAMPLE')
    print(df.head())

    # Upload to the database
    with engine.connect() as conn:
        df.to_sql('gatk_baf', con=conn, if_exists='replace', index=True, index_label='SAMPLE')
        print("Data uploaded successfully.")

def upload_table_hgnc():
    # Complete set of human genes with current symbols, current aliases and previous symbols
    # useful for interchangeable gene names like MMSET and NSD2
    df = pd.read_csv(f'./refdata/hgnc_nomenclature.tsv', sep='\t').rename(columns={'Ensembl gene ID': 'Gene stable ID',
                                                                                   'Approved symbol': 'Gene symbol',
                                                                                   'Approved name':   'Gene name'})
    df = df.set_index(['Gene stable ID','Gene symbol'])
    print(df.head())

    # Upload to the database
    with engine.connect() as conn:
        df.to_sql('hgnc_nomenclature', con=conn, if_exists='replace', index=True, index_label=['Gene stable ID','Gene symbol'])
        print("Data uploaded successfully.")

if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    assert load_dotenv('src/.env')
    db_uri = os.environ.get("COMMPASS_DB_URI")
    engine = create_engine(db_uri)

    with engine.connect() as conn:
        # test connection
        result = conn.execute(text("SELECT version();"))
        print(result.fetchone())
        # upload tables
        upload_table_per_patient()
        upload_table_per_patient_visit()
        upload_table_stand_alone_survival()
        upload_table_stand_alone_treatment_regimen()
        upload_table_stand_alone_trtresp()
        upload_table_salmon_gene_unstranded_counts()
        upload_table_salmon_gene_unstranded_tpm()
        upload_table_genome_gatk_cna()
        upload_table_gene_annotation()
        upload_table_exome_NS_variants()
        upload_table_canonical_ig()
        upload_table_wgs_fish()
        upload_table_sbs()
        upload_table_chromothripsis()
        upload_table_gep_scores()
        upload_table_baf()
        upload_table_hgnc()
        exit()

