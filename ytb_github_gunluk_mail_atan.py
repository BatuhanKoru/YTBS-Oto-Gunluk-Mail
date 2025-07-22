import os
import time
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders
from datetime import date, timedelta

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

# --- PROJE AYARLARI ---
DOWNLOAD_KLASORU = "Gunluk_TEIAS_Raporlari"
URL = "https://ytbsbilgi.teias.gov.tr/ytbsbilgi/frm_istatistikler.jsf"


# --- E-POSTA GÖNDERME FONKSİYONU (GÜVENLİ VERSİYON) ---
def eposta_gonder(dosya_yolu, dosya_adi):
    # Gizli bilgileri GitHub Secrets'tan (ortam değişkenlerinden) alıyoruz
    gonderen_mail = os.environ.get('GMAIL_ADDRESS')
    gonderen_sifre = os.environ.get('GMAIL_APP_PASSWORD')  # Bu, uygulama şifresi olacak
    alici_mail = os.environ.get('RECIPIENT_EMAIL')

    if not all([gonderen_mail, gonderen_sifre, alici_mail]):
        print("❌ E-posta bilgileri (GMAIL_ADDRESS, GMAIL_APP_PASSWORD, RECIPIENT_EMAIL) GitHub Secrets'ta eksik!")
        return

    print(f"📬 E-posta hazırlanıyor: '{alici_mail}' adresine gönderilecek...")

    msg = MIMEMultipart()
    msg['From'] = gonderen_mail
    msg['To'] = alici_mail

    dunun_tarihi_str = (date.today() - timedelta(days=1)).strftime("%d-%m-%Y")
    msg['Subject'] = f"TEİAŞ Günlük Raporu ({dunun_tarihi_str})"

    body = f"Merhaba,\n\n{dunun_tarihi_str} tarihli TEİAŞ Yük Tevzi Bilgi Sistemi günlük raporu ektedir.\n\nBu e-posta otomatik olarak gönderilmiştir."
    msg.attach(MIMEText(body, 'plain'))

    try:
        with open(dosya_yolu, "rb") as attachment:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(attachment.read())
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', f"attachment; filename= {dosya_adi}")
        msg.attach(part)
        print(f"📎 '{dosya_adi}' dosyası e-postaya eklendi.")
    except Exception as e:
        print(f"❌ Dosya eklenirken hata oluştu: {e}")
        return

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(gonderen_mail, gonderen_sifre)
        text = msg.as_string()
        server.sendmail(gonderen_mail, alici_mail, text)
        server.quit()
        print("✅ E-posta başarıyla gönderildi!")
    except Exception as e:
        print(f"❌ E-posta gönderilirken bir hata oluştu: {e}")


# --- ANA KOD BLOGU ---
def raporu_indir_ve_gonder():
    # ... Bu fonksiyonun geri kalanı sizin dosyanızdaki ile aynı kalabilir,
    # Sadece dosya adını doğru kullandığımızdan emin olalım:
    # rapor_indirici_epostali.py yerine ytb_github_gunluk_mail_atan.py

    print("✅ Otomasyon başlatılıyor... (GitHub Secrets Sürümü)")
    dun = date.today() - timedelta(days=1)
    dunun_tarihi_str = dun.strftime("%d-%m-%Y")
    print(f"📅 Rapor tarihi olarak hesaplanan gün: {dunun_tarihi_str}")

    indirilecek_tam_yol = os.path.join(os.getcwd(), DOWNLOAD_KLASORU)
    if not os.path.exists(indirilecek_tam_yol):
        os.makedirs(indirilecek_tam_yol)

    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")

    prefs = {"download.default_directory": indirilecek_tam_yol}
    chrome_options.add_experimental_option("prefs", prefs)

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

    indirilen_dosya_yolu = ""
    try:
        print(f"🌍 '{URL}' adresine gidiliyor...")
        driver.get(URL)
        wait = WebDriverWait(driver, 30)

        try:
            kabul_et_butonu = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "button[id$='btnKabul']")))
            kabul_et_butonu.click()
            time.sleep(2)
        except TimeoutException:
            pass

        tarih_input = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "input[id$='bitisTarihi2_input']")))
        driver.execute_script(f"arguments[0].value='{dunun_tarihi_str}';", tarih_input)
        time.sleep(1)

        goster_butonu = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button[id$='gunlukRapor']")))
        goster_butonu.click()
        time.sleep(5)

        excel_butonu = wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "input[type='image'][src*='excel.png']")))
        excel_butonu.click()
        print("✔️ Rapor indirme işlemi başlatıldı.")

        print("📥 Dosyanın indirilmesi bekleniyor...")
        time.sleep(15)

        files = os.listdir(indirilecek_tam_yol)
        if files:
            indirilen_dosya_adi = files[0]
            indirilen_dosya_yolu = os.path.join(indirilecek_tam_yol, indirilen_dosya_adi)
            print(f"👍 Dosya başarıyla indirildi: {indirilen_dosya_adi}")
        else:
            raise Exception("İndirme klasörü boş, dosya indirilemedi!")

    except Exception as e:
        print(f"❌ Rapor indirilirken bir hata oluştu: {e}")
    finally:
        driver.quit()

    if indirilen_dosya_yolu:
        eposta_gonder(indirilen_dosya_yolu, indirilen_dosya_adi)


if __name__ == "__main__":
    raporu_indir_ve_gonder()