# Guía: Configurar Acceso Automático a Google Sheets

Sigue estos pasos para obtener el archivo `credentials.json` que permitirá al sistema actualizar tu hoja automáticamente.

---

### 1. Crear Proyecto y Habilitar API
1.  Ve a la [Calculadora de Consola de Google Cloud](https://console.cloud.google.com/flows/enableapi?apiid=sheets.googleapis.com).
2.  Selecciona **"Crear un proyecto"** y dale un nombre (ej. `AntigravityTrading`).
3.  Haz clic en **"Siguiente"** y luego en **"Habilitar"** (Enable). Esto activará la Google Sheets API.

### 2. Crear la "Cuenta de Servicio" (El Robot)
1.  Ve a la sección de [Credenciales](https://console.cloud.google.com/apis/credentials).
2.  Haz clic en **"Crear Credenciales"** > **"Cuenta de servicio"**.
3.  Ponle un nombre (ej. `bot-trading`) y dale a "Crear y Continuar".
4.  En "Otorgar acceso", selecciona el rol **"Propietario"** (Owner) o "Editor". Dale a "Continuar" y luego "Listo".

### 3. Descargar la Llave (`credentials.json`)
1.  En la lista de "Cuentas de servicio", haz clic en el email del bot que acabas de crear (ej. `bot-trading@...`).
2.  Ve a la pestaña **"Claves"** (Keys).
3.  Haz clic en **"Agregar clave"** > **"Crear clave nueva"**.
4.  Selecciona **JSON** y dale a "Crear".
5.  **Se descargará un archivo automáticamente.** 
    *   Renómbralo a: `credentials.json`
    *   Muévelo a la carpeta: `d:\python\infoacc\infoacc\`

### 4. Compartir la Hoja con el Robot
1.  Abre el archivo JSON que descargaste con el Bloc de Notas.
2.  Busca la línea que dice `"client_email"`. Copia ese correo (algo como `bot-trading@proyecto.iam.gserviceaccount.com`).
3.  Ve a tu **Google Sheet** (la que creaste en el navegador).
4.  Haz clic en el botón **"Compartir"** (arriba a la derecha).
5.  Pega el correo del bot y dale permisos de **Editor**.
6.  Desmarca "Notificar a los usuarios" (opcional) y dale a "Compartir".

---

✅ **Una vez tengas el archivo `credentials.json` en `d:\python\infoacc\infoacc\`, avísame y programaré el script.**
