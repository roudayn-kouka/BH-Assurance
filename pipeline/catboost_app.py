from fastapi import FastAPI
import pandas as pd
from db_utils import get_connection  # ✅ absolute import

app = FastAPI()

@app.post("/build_catboost_table")
def build_catboost_table():
    with get_connection() as conn:
        # 1. Charger test_pp
        query = """
            SELECT 
                REF_pp, Situation_Familiale, Lib_Secteur_Activite, Lib_Profession,
                Age_Contrat, Lib_Produit, Category, Candidate_Produit, Num_Contrat,
                Lib_Branche, Lib_Sous_Branche, Age
            FROM dbo.test_pp
            WHERE Decision = 'recommend'
        """
        df = pd.read_sql(query, conn)

        # 2. Split Candidate_Produit en plusieurs lignes
        df_exploded = (
            df.assign(Candidate_Produit=df["Candidate_Produit"].str.split(";"))
              .explode("Candidate_Produit")
        )
        df_exploded["Candidate_Produit"] = df_exploded["Candidate_Produit"].str.strip()

        # 3. Colonne Bought
        df_exploded["Bought"] = (df_exploded["Candidate_Produit"] == df_exploded["Lib_Produit"]).astype(int)

        # 4. Supprimer et recréer la table
        cursor = conn.cursor()
        cursor.execute("""
            IF OBJECT_ID('dbo.catboost_produits_pp', 'U') IS NOT NULL 
                DROP TABLE dbo.catboost_produits_pp;
        """)
        conn.commit()

        create_table_sql = """
        CREATE TABLE dbo.catboost_produits_pp (
            REF_pp BIGINT,
            Situation_Familiale NVARCHAR(MAX),
            Lib_Secteur_Activite NVARCHAR(MAX),
            Lib_Profession NVARCHAR(MAX),
            Age_Contrat NVARCHAR(MAX),
            Lib_Produit NVARCHAR(MAX),
            Category NVARCHAR(MAX),
            Candidate_Produit NVARCHAR(MAX),
            Num_Contrat BIGINT,
            Lib_Branche NVARCHAR(200),
            Lib_Sous_Branche NVARCHAR(200),
            Age INT,
            Bought BIT
        )
        """
        cursor.execute(create_table_sql)
        conn.commit()

        # 5. Insert ligne par ligne
        for _, row in df_exploded.iterrows():
            cursor.execute("""
                INSERT INTO dbo.catboost_produits_pp
                (REF_pp, Situation_Familiale, Lib_Secteur_Activite, Lib_Profession,
                 Age_Contrat, Lib_Produit, Category, Candidate_Produit, Num_Contrat,
                 Lib_Branche, Lib_Sous_Branche, Age, Bought)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, tuple(row))
        conn.commit()

    return {"status": "success", "rows_inserted": len(df_exploded)}

# --- Preview endpoint ---
@app.get("/catboost_preview")
def preview_catboost():
    with get_connection() as conn:
        df = pd.read_sql("SELECT TOP 10 * FROM dbo.catboost_produits_pp", conn)
    return {"preview": df.to_dict(orient="records")}
