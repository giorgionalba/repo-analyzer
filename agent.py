import os
import json
from groq import Groq
from dotenv import load_dotenv
import git
import tempfile

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def clonar_repo(url):
    carpeta = tempfile.mkdtemp()
    git.Repo.clone_from(url, carpeta)
    return carpeta

def listar_archivos(carpeta, max_archivos=50):
    archivos = []
    for root, dirs, files in os.walk(carpeta):
        dirs[:] = [d for d in dirs if d not in ['.git', 'node_modules', 'venv']]
        for file in files:
            path = os.path.join(root, file)
            path_relativo = path.replace(carpeta, '')
            archivos.append(path_relativo)
            if len(archivos) >= max_archivos:
                return archivos
    return archivos

def leer_archivo(carpeta, path):
    try:
        full_path = carpeta + path
        with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
            contenido = f.read(3000)
        return contenido
    except Exception as e:
        return f"Error leyendo archivo: {e}"

def analizar_repo(url):
    print(f"Clonando {url}...")
    carpeta = clonar_repo(url)

    tools = [
        {
            "type": "function",
            "function": {
                "name": "listar_archivos",
                "description": "Lista los archivos del repositorio",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "leer_archivo",
                "description": "Lee el contenido de un archivo específico",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "El path del archivo a leer"
                        }
                    },
                    "required": ["path"]
                }
            }
        }
    ]

    messages = [
        {
            "role": "user",
            "content": "Analizá este repositorio y generá un reporte con: qué hace el proyecto, qué tecnologías usa, y 3 sugerencias de mejora."
        }
    ]

    print("Agente analizando...")

    while True:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            max_tokens=4096,
            tools=tools,
            messages=messages
        )

        message = response.choices[0].message
        finish_reason = response.choices[0].finish_reason

        assistant_msg = {"role": "assistant", "content": message.content or ""}
        if message.tool_calls:
            assistant_msg["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {"name": tc.function.name, "arguments": tc.function.arguments}
                }
                for tc in message.tool_calls
            ]
        messages.append(assistant_msg)

        if finish_reason == "stop":
            print("\n=== REPORTE ===\n")
            print(message.content)
            break

        if message.tool_calls:
            for tc in message.tool_calls:
                print(f"El agente está usando: {tc.function.name}")
                args = json.loads(tc.function.arguments)

                if tc.function.name == "listar_archivos":
                    resultado = listar_archivos(carpeta)
                elif tc.function.name == "leer_archivo":
                    resultado = leer_archivo(carpeta, args["path"])
                else:
                    resultado = "Herramienta desconocida"

                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": str(resultado)
                })

if __name__ == "__main__":
    url = input("URL del repo a analizar: ")
    analizar_repo(url)
