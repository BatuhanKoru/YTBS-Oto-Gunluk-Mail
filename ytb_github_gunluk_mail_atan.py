import os
import time
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders
from datetime import date, timedelta

# Selenium yerine yeni kütüphanelerimizi ekliyoruz
import requests
from bs4 import BeautifulSoup

# --- PROJE AYARLARI ---
DOWNLOAD_KLASORU = "Gunluk_TEIAS_Raporlari"
URL = "https://ytbsbilgi.teias.gov.tr/ytbsbilgi/frm_istatistikler.jsf"


# --- E-POSTA GÖNDERME FONKSİYONU (Aynı kalıyor) ---
def eposta_gonder(dosya_yolu, dosya_adi):
    gonderen_mail = os.environ.get('GMAIL_ADDRESS')
    gonderen_sifre = os.environ.get('GMAIL_APP_PASSWORD')
    alici_mail = os.environ.get('RECIPIENT_EMAIL')
    if not all([gonderen_mail, gonderen_sifre, alici_mail]):
        print("❌ E-posta bilgileri GitHub Secrets'ta eksik!")
        return
    print(f"📬 E-posta hazırlanıyor: '{alici_mail}' adresine gönderilecek...")
    msg = MIMEMultipart()
    msg['From'] = gonderen_mail
    msg['To'] = alici_mail
    msg['Subject'] = f"TEİAŞ Günlük Raporu ({dosya_adi.split('_')[-1].replace('.xlsx', '')})"
    body = f"Merhaba,\n\n{dosya_adi.split('_')[-1].replace('.xlsx', '')} tarihli TEİAŞ raporu ektedir.\n\nBu e-posta otomatik olarak gönderilmiştir."
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


# --- ANA KOD BLOGU (YENİ YÖNTEM) ---
def raporu_indir_ve_gonder_tarayicisiz():
    print("✅ Otomasyon başlatılıyor... (Tarayıcısız - Direkt İstek Sürümü)")

    # 1. Dünün tarihini hem 'GG-AA-YYYY' hem de 'YYYY-MM-DD' formatında hazırlıyoruz
    dun = date.today() - timedelta(days=1)
    tarih_form_icin = dun.strftime("%d-%m-%Y")
    tarih_dosya_icin = dun.strftime("%Y-%m-%d")
    print(f"📅 Rapor tarihi olarak '{tarih_form_icin}' kullanılacak.")

    # 2. İndirme klasörünü oluştur
    indirilecek_klasor_yolu = os.path.join(os.getcwd(), DOWNLOAD_KLASORU)
    if not os.path.exists(indirilecek_klasor_yolu):
        os.makedirs(indirilecek_klasor_yolu)

    # 3. Oturumu başlat ve gizli anahtarı (ViewState) al
    try:
        print("🌍 Sunucuya bağlanılıyor ve oturum anahtarı (ViewState) alınıyor...")
        # requests.Session() çerezleri ve oturum bilgilerini otomatik yönetir
        session = requests.Session()

        # Siteye ilk "merhaba" isteğini gönderiyoruz
        ilk_yanit = session.get(URL, timeout=30)
        ilk_yanit.raise_for_status()  # Hata varsa programı durdur

        # BeautifulSoup ile HTML'i analiz edip gizli ViewState'i buluyoruz
        soup = BeautifulSoup(ilk_yanit.content, 'html.parser')
        view_state = soup.find('input', {'name': 'jakarta.faces.ViewState'}).get('value')
        print("✔️ Oturum anahtarı başarıyla alındı.")
    except Exception as e:
        print(f"❌ Sitenin ilk açılışında veya ViewState alınırken hata oluştu: {e}")
        return

    # 4. Excel'i indirmek için gerekli olan Form Verisini hazırla
    form_verisi = {
        "formdash": "formdash",
        "hidden1": "13",
        "formdash:bitisTarihi2_input": tarih_form_icin,
        # Bu satır, "Göster" yerine "Excel" butonuna bastığımızı belirtir.
        # HTML kodunu inceleyerek bu ID'yi bulduk.
        "formdash:j_idt45": "formdash:j_idt45",
        "formdash:yilsecim_focus": "",
        "formdash:yilsecim_input": dun.year,
        "jakarta.faces.ViewState": view_state
    }

    # 5. Dosyayı indirme isteğini gönder
    try:
        print("📥 Excel dosyası için indirme isteği gönderiliyor...")
        # Aynı oturumla, hazırladığımız form verisini sunucuya POST metoduyla gönderiyoruz
        excel_yaniti = session.post(URL, data=form_verisi, timeout=30)
        excel_yaniti.raise_for_status()

        # Dosya adını ve tam yolunu oluştur
        dosya_adi = f"GENEL_GUNLUK_ISLETME_NETICESI_{tarih_dosya_icin}.xlsx"
        dosya_yolu = os.path.join(indirilecek_klasor_yolu, dosya_adi)

        # Sunucudan gelen dosya içeriğini diske yaz
        with open(dosya_yolu, 'wb') as f:
            f.write(excel_yaniti.content)

        print(f"👍 Dosya başarıyla indirildi: {dosya_adi}")

        # 6. E-posta gönder
        eposta_gonder(dosya_yolu, dosya_adi)

    except requests.exceptions.RequestException as e:
        print(f"❌ Dosya indirilirken bir ağ hatası oluştu: {e}")
    except Exception as e:
        print(f"❌ Dosya indirme veya e-posta gönderme sırasında beklenmedik bir hata oluştu: {e}")


if __name__ == "__main__":
    raporu_indir_ve_gonder_tarayicisiz()