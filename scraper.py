import pandas as pd
from datetime import datetime, timedelta
import time
import os

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# =========================================================
# CONFIG
# =========================================================
CARPETA = "ArchBIV"
ARCHIVO = f"{CARPETA}/volumen_historico_emmsa.csv"

os.makedirs(CARPETA, exist_ok=True)


# =========================================================
# DRIVER
# =========================================================
def get_driver():

    options = Options()

    # LOCAL -> comentar para ver navegador
    # options.add_argument("--headless=new")

    # GITHUB ACTIONS
    if os.getenv("GITHUB_ACTIONS"):

        options.add_argument("--headless=new")

        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")

    options.add_argument("--start-maximized")

    options.add_argument(
        "--disable-blink-features=AutomationControlled"
    )

    options.page_load_strategy = "eager"

    # LOCAL
    if not os.getenv("GITHUB_ACTIONS"):

        service = Service(
            ChromeDriverManager().install()
        )

        driver = webdriver.Chrome(
            service=service,
            options=options
        )

    # GITHUB
    else:

        driver = webdriver.Chrome(options=options)

    driver.set_page_load_timeout(180)

    return driver

# =========================================================
# GENERAR FECHAS (AYER Y HOY)
# =========================================================
def generar_fechas():

    hoy = datetime.now()

    ayer = hoy - timedelta(days=1)

    return [
        ayer.strftime("%d/%m/%Y"),
        hoy.strftime("%d/%m/%Y")
    ]

def entrar_iframe(driver):

    WebDriverWait(driver, 40).until(
        EC.frame_to_be_available_and_switch_to_it(
            (By.TAG_NAME, "iframe")
        )
    )


def seleccionar_volumen(driver):

    print("📦 Cambiando a VOLUMEN...")

    radios = driver.find_elements(
        By.CSS_SELECTOR,
        "input[type='radio']"
    )

    for r in radios:

        value = r.get_attribute("value")

        # volumen = 2
        if value == "2":

            driver.execute_script("""
                arguments[0].checked = true;
                arguments[0].click();
            """, r)

            time.sleep(3)

            print("✅ VOLUMEN seleccionado")

            return

    raise Exception("❌ No se encontró VOLUMEN")

def escribir_fecha(driver, fecha):

    print(f"📅 Fecha: {fecha}")

    fecha_input = WebDriverWait(driver, 40).until(
        EC.presence_of_element_located(
            (By.ID, "txtfecha1")
        )
    )

    driver.execute_script(
        "arguments[0].value = '';",
        fecha_input
    )

    driver.execute_script(
        "arguments[0].value = arguments[1];",
        fecha_input,
        fecha
    )

    driver.execute_script("""
        arguments[0].dispatchEvent(new Event('change'));
        arguments[0].dispatchEvent(new Event('input'));
    """, fecha_input)

    time.sleep(2)

def seleccionar_todos(driver):

    print("📦 Seleccionando todos los productos...")

    checks = driver.find_elements(
        By.CSS_SELECTOR,
        "input[type='checkbox']"
    )

    for c in checks:

        try:

            if not c.is_selected():

                driver.execute_script(
                    "arguments[0].click();",
                    c
                )

        except:
            pass

    time.sleep(3)

    print("✅ Productos seleccionados")


# =========================================================
# CONSULTAR
# =========================================================
def consultar(driver):

    print("🔎 Consultando...")

    boton = WebDriverWait(driver, 40).until(
        EC.element_to_be_clickable(
            (
                By.XPATH,
                "//button[contains(text(),'Consultar')]"
            )
        )
    )

    driver.execute_script(
        "arguments[0].click();",
        boton
    )

    time.sleep(10)

    print("✅ Consulta realizada")


# =========================================================
# LEER TABLA
# =========================================================
def leer_tabla(driver, fecha):

    try:

        print("📊 Leyendo tabla...")

        WebDriverWait(driver, 60).until(

            lambda d: len(
                d.find_elements(
                    By.CSS_SELECTOR,
                    ".dataTables_scrollBody tr"
                )
            ) > 1
        )

    except Exception as e:

        print("❌ Tabla no encontrada")
        print(e)

        return None

    headers = [
        th.text.strip()
        for th in driver.find_elements(By.TAG_NAME, "th")
    ]

    filas = driver.find_elements(
        By.CSS_SELECTOR,
        ".dataTables_scrollBody tr"
    )

    datos = []

    for fila in filas:

        celdas = fila.find_elements(By.TAG_NAME, "td")

        textos = [
            td.text.strip()
            for td in celdas
        ]

        if len(textos) > 1:

            datos.append(textos)

    if not datos:

        return None

    headers = headers[:len(datos[0])]

    df = pd.DataFrame(
        datos,
        columns=headers
    )

    df["Fecha"] = fecha

    print(f"✅ Filas: {len(df)}")

    return df


# =========================================================
# GUARDAR HISTÓRICO
# =========================================================
def guardar_historico(nuevos):

    # archivo existente
    if os.path.exists(ARCHIVO):

        try:

            old = pd.read_csv(ARCHIVO)

        except:

            old = pd.DataFrame()

    else:

        old = pd.DataFrame()

    # unir histórico + nuevos
    final = pd.concat(
        [old] + nuevos,
        ignore_index=True
    )

    # quitar duplicados
    final.drop_duplicates(inplace=True)

    # ordenar por fecha
    if "Fecha" in final.columns:

        final["Fecha_dt"] = pd.to_datetime(
            final["Fecha"],
            format="%d/%m/%Y",
            errors="coerce"
        )

        final = final.sort_values(
            "Fecha_dt"
        )

        final.drop(
            columns=["Fecha_dt"],
            inplace=True
        )

    # guardar
    final.to_csv(
        ARCHIVO,
        index=False,
        encoding="utf-8-sig"
    )

    print("💾 HISTÓRICO ACTUALIZADO")

    print(final.tail())


# =========================================================
# SCRAPER FECHA
# =========================================================
def scrapear_fecha(driver, fecha):

    print("\n===================================")
    print(f"🔎 SCRAPING {fecha}")
    print("===================================")

    url = "https://www.emmsa.com.pe/index.php/precios-diarios/"

    driver.get(url)

    # iframe
    entrar_iframe(driver)

    # volumen
    seleccionar_volumen(driver)

    # refrescar iframe
    driver.switch_to.default_content()

    time.sleep(3)

    entrar_iframe(driver)

    # fecha
    escribir_fecha(driver, fecha)

    # productos
    seleccionar_todos(driver)

    # consultar
    consultar(driver)

    # volver iframe
    driver.switch_to.default_content()

    time.sleep(3)

    entrar_iframe(driver)

    # leer tabla
    df = leer_tabla(driver, fecha)

    return df
# =========================================================
# MAIN
# =========================================================
def main():

    print("📡 EMMSA HISTÓRICO VOLUMEN")

    fechas = generar_fechas()

    print(f"📅 Total fechas: {len(fechas)}")

    # histórico existente
    if os.path.exists(ARCHIVO):

        try:

            old = pd.read_csv(ARCHIVO)

        except:

            old = pd.DataFrame()

    else:

        old = pd.DataFrame()

    # fechas ya existentes
    if not old.empty and "Fecha" in old.columns:

        fechas_existentes = set(
            old["Fecha"].astype(str)
        )

    else:

        fechas_existentes = set()

    driver = get_driver()

    nuevos = []

    try:

        for i, fecha in enumerate(fechas, start=1):

            print(f"\n📅 [{i}/{len(fechas)}] {fecha}")

            # evitar duplicados
            if fecha in fechas_existentes:

                print("✔ Ya existe en histórico")

                continue

            try:

                df = scrapear_fecha(
                    driver,
                    fecha
                )

                if df is not None:

                    nuevos.append(df)

                    print("✅ Datos agregados")

                else:

                    print("⚠ Sin datos")

            except Exception as e:

                print("❌ Error scraping")
                print(e)

            time.sleep(3)

    finally:

        driver.quit()

    # guardar histórico
    if nuevos:

        guardar_historico(nuevos)

    else:

        print("ℹ No hubo datos nuevos")

# =========================================================
# START
# =========================================================
if __name__ == "__main__":

    main()