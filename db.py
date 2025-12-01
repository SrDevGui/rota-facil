from datetime import date

#Como seria +- um banco de dados

VIAGENS = [
    {"origem": "Goiânia", "destino": "Manaus", "data": "2025-10-25", "vagas": 5},
    {"origem": "Goiânia", "destino": "São Paulo", "data": "2025-10-22", "vagas": 0},
    {"origem": "Manaus", "destino": "Goiânia", "data": "2025-10-23", "vagas": 2},
]

#Query
def consultar_viagem(origem, destino, data):
    print(f"Consultando origem {origem}, destino {destino}, data {data}")
    for viagem in VIAGENS:
        if (
            viagem["origem"].lower() == origem.lower()
            and viagem["destino"].lower() == destino.lower()
            and viagem["data"] == data
        ):
            return viagem
    return None

# #Testes separados (Deixar comentado)
# res = consultar_viagem("Goiânia", "Manaus", "2025-10-25") #Supondo que queremos saber se tem vaga entre esses destinos no dia 25/10
# print(res["vagas"]) #A consulta deve retornar 5

#No momento só vai responder a perguntas como:
# Tem vaga pra passagem de Goiânia pra Manaus no dia 2025-10-25?