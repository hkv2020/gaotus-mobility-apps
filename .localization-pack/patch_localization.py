from pathlib import Path
import re, sys

if len(sys.argv) != 2 or sys.argv[1] not in {'driver','passenger'}:
    raise SystemExit('usage: patch_localization.py driver|passenger')
name=sys.argv[1]
root=Path(name)
if not root.exists():
    raise SystemExit(f'{name} source directory missing')

translations={
'Home':'Acasă','Jobs':'Comenzi','Map':'Hartă','Chat':'Chat','Earnings':'Câștiguri','Menu':'Meniu','Login':'Autentificare','Sign in':'Autentificare','Continue':'Continuă','Save':'Salvează','Cancel':'Anulează','Close':'Închide','Refresh':'Actualizează','Retry':'Reîncearcă','Back':'Înapoi','Done':'Gata','Next':'Următorul','Driver':'Șofer','Passenger':'Pasager','Customer':'Client','Vehicle':'Vehicul','Status':'Status','Route':'Rută','Pickup':'Preluare','Destination':'Destinație','Delivery':'Livrare','Collection':'Colectare','Ride':'Cursă','Deliveries':'Livrări','Rides':'Curse','Collections':'Colectări','Stops':'Opriri','Stop':'Oprire','Profile':'Profil','Settings':'Setări','Support':'Asistență','Account':'Cont','History':'Istoric','Phone number':'Număr de telefon','Email':'Email','Password':'Parolă','First name':'Prenume','Last name':'Nume','Company server':'Server companie','Connection settings':'Setări conexiune','Create account':'Creează cont','Online':'Online','Offline':'Offline','Available':'Disponibil','Busy':'Ocupat','Accepted':'Acceptată','Declined':'Refuzată','Pending':'În așteptare','Assigned':'Alocată','Completed':'Finalizată','Cancelled':'Anulată','Failed':'Eșuată','Postponed':'Amânată','Arrived':'Ajuns','Navigate':'Navighează','Call':'Sună','Start':'Pornește','Finish':'Finalizează','Confirm':'Confirmă','Accept':'Acceptă','Decline':'Refuză','Today':'Astăzi','Week':'Săptămână','Month':'Lună','Total':'Total','Cash':'Numerar','Card':'Card','Notes':'Note','Reason':'Motiv','Address':'Adresă','Recipient':'Destinatar','Signature':'Semnătură','Photo':'Fotografie','Proof':'Dovadă','Barcode':'Cod de bare','Reference':'Referință','Packages':'Colete',
'No active job.':'Nu există nicio comandă activă.','No active operations job.':'Nu există nicio operațiune activă.','No active trip.':'Nu există nicio cursă activă.','Could not open navigation.':'Nu s-a putut deschide navigația.','Could not open the phone app.':'Nu s-a putut deschide aplicația de telefon.','Could not update stop.':'Oprirea nu a putut fi actualizată.','Operations job completed.':'Operațiunea a fost finalizată.','Failed delivery / collection':'Livrare / colectare eșuată','Postpone stop':'Amână oprirea','Customer unavailable, access issue…':'Client indisponibil, problemă de acces…','Route stops':'Opririle rutei','Start route to stop':'Pornește ruta către oprire','I’ve arrived':'Am ajuns','Complete with proof':'Finalizează cu dovadă','Take a proof photo before completing this stop.':'Fă o fotografie ca dovadă înainte de finalizarea acestei opriri.','Recipient name is required.':'Numele destinatarului este obligatoriu.','Confirmation PIN is required.':'PIN-ul de confirmare este obligatoriu.','Barcode / reference is required.':'Codul de bare / referința este obligatoriu.','Recipient signature is required.':'Semnătura destinatarului este obligatorie.',
'Create your account':'Creează-ți contul','Get moving':'Pornește la drum','Book, track and manage every ride from one place.':'Rezervă, urmărește și gestionează toate cursele dintr-un singur loc.','Sign in to book a ride and follow your driver live.':'Autentifică-te pentru a rezerva o cursă și a urmări șoferul în timp real.','Email or username':'Email sau nume de utilizator','Already have an account? Sign in':'Ai deja cont? Autentifică-te','New here? Create an account':'Ești nou? Creează un cont','By continuing you agree to the service terms and privacy policy.':'Continuând, accepți termenii serviciului și politica de confidențialitate.',
'Cancel this ride?':'Anulezi această cursă?','Your driver may already be travelling to you. Cancellation fees are not automated in this staging build.':'Șoferul poate fi deja în drum spre tine. Taxele de anulare nu sunt automatizate în această versiune.','Cancel ride':'Anulează cursa','Keep ride':'Păstrează cursa','How was your trip?':'Cum a fost cursa?','Anything we should know? (optional)':'Mai este ceva ce ar trebui să știm? (opțional)','Send rating':'Trimite evaluarea','Rate this trip':'Evaluează cursa','Share trip status':'Distribuie statusul cursei','Share your live ride details with someone you trust':'Trimite detaliile cursei în timp real unei persoane de încredere','Contact support':'Contactează asistența','Support workflow will be connected next':'Fluxul de asistență va fi conectat în etapa următoare','Payment required':'Plată necesară','Finding your driver':'Căutăm un șofer','Meet your driver':'Întâlnește șoferul','Your driver is on the way':'Șoferul este în drum','Your driver has arrived':'Șoferul a ajuns','You are on your way':'Ești în drum spre destinație','Trip completed':'Cursă finalizată','Ride cancelled':'Cursă anulată','Ride update':'Actualizare cursă','We are matching you with an available driver.':'Căutăm un șofer disponibil pentru tine.','Driver details are ready below.':'Detaliile șoferului sunt disponibile mai jos.','Follow the car live on the map.':'Urmărește mașina în timp real pe hartă.','Please meet your driver at the pick-up point.':'Te rugăm să întâlnești șoferul la punctul de preluare.','Relax — your trip is in progress.':'Cursa este în desfășurare.','Thanks for riding with us.':'Îți mulțumim că ai călătorit cu noi.','We will keep this screen updated automatically.':'Acest ecran se actualizează automat.','Your driver':'Șoferul tău','Driver location live':'Locația șoferului în timp real',
'Cancel delivery?':'Anulezi livrarea?','The driver may already be travelling to the collection point.':'Șoferul poate fi deja în drum către punctul de colectare.','Keep delivery':'Păstrează livrarea','Cancel delivery':'Anulează livrarea','Send a parcel':'Trimite un colet','Business delivery':'Livrare business','Book a ride':'Rezervă o cursă','Where to?':'Unde mergi?','Where from?':'De unde?','Choose pickup':'Alege preluarea','Choose destination':'Alege destinația','Confirm pickup':'Confirmă preluarea','Get quote':'Calculează prețul','Book now':'Rezervă acum','Track delivery':'Urmărește livrarea','Delivery completed':'Livrare finalizată','Delivery cancelled':'Livrare anulată','Driver assigned':'Șofer alocat','Driver on the way':'Șoferul este în drum','Trip started':'Cursa a început','Delivery in progress':'Livrare în desfășurare','Your ride has an update.':'Cursa ta are o actualizare.','Your delivery has an update.':'Livrarea ta are o actualizare.',
'Current job':'Comanda curentă','Available jobs':'Comenzi disponibile','No jobs available':'Nu sunt comenzi disponibile','Trip extras':'Extra cursă','No extras added. Automatic waiting time will appear here when applicable.':'Nu există extra-uri. Timpul de așteptare automat va apărea aici când este cazul.','Extras total':'Total extra-uri','Add extra':'Adaugă extra','No messages yet.':'Nu există mesaje.','Message passenger…':'Mesaj către pasager…','Driver settings':'Setări șofer','Save to Platform':'Salvează în Platformă','No Platform data recorded yet.':'Nu există încă date înregistrate în Platformă.','Completed trips':'Curse finalizate','Safety & support':'Siguranță și asistență','Complete payment':'Finalizează plata','I have paid — refresh':'Am plătit — actualizează','Delivery route':'Ruta livrării',
'Message from your driver':'Mesaj de la șofer','You have a new ride message.':'Ai un mesaj nou despre cursă.','A driver has accepted your delivery.':'Un șofer a acceptat livrarea.','Your driver has accepted the ride.':'Șoferul a acceptat cursa.','Your driver is travelling to the next delivery stop.':'Șoferul se deplasează către următoarea oprire.','Your driver is travelling to the pickup point.':'Șoferul se deplasează către punctul de preluare.','Your driver has arrived at the next stop.':'Șoferul a ajuns la următoarea oprire.','Your driver is waiting at the pickup point.':'Șoferul te așteaptă la punctul de preluare.','Your delivery is now in progress.':'Livrarea este acum în desfășurare.','Your trip is now in progress.':'Cursa este acum în desfășurare.','Your delivery has been completed.':'Livrarea a fost finalizată.','Your delivery has been cancelled.':'Livrarea a fost anulată.','Your ride has been cancelled.':'Cursa a fost anulată.','Your delivery status has changed.':'Statusul livrării s-a schimbat.','Your ride status has changed.':'Statusul cursei s-a schimbat.'
}

loc_lines=["import 'country_config.dart';",'', 'class AppLocalization {','  AppLocalization._();',"  static bool get isRomanian => CountryConfig.language.toLowerCase().startsWith('ro');",'  static const Map<String,String> _ro = <String,String>{']
for k,v in translations.items():
    def dq(x): return '"'+x.replace('\\','\\\\').replace('"','\\"').replace('$','\\$')+'"'
    loc_lines.append(f'    {dq(k)}: {dq(v)},')
loc_lines += ['  };','  static String t(String source) {',"    if (!isRomanian || source.isEmpty) return source;",'    return _ro[source] ?? source;','  }','}','','extension GaotusLocalizedString on String {','  String get tr => AppLocalization.t(this);','}']
(root/'lib/core/localization.dart').write_text('\n'.join(loc_lines)+'\n')

cc=root/'lib/core/country_config.dart'
txt=cc.read_text()
if "static String language" not in txt:
    txt=txt.replace("  static String units = 'imperial';", "  static String units = 'imperial';\n  static String language = 'en';")
if name=='passenger' and "language = 'en';" not in txt.split('static void reset()',1)[1].split('}',1)[0]:
    txt=txt.replace("timezone = 'Europe/London'; phonePrefix = '+44'; units = 'imperial';", "timezone = 'Europe/London'; phonePrefix = '+44'; units = 'imperial'; language = 'en';")
if name=='driver':
    txt=txt.replace("    units = (raw['units'] ?? units).toString();", "    units = (raw['units'] ?? raw['unit_system'] ?? units).toString();\n    final rawLanguage = (raw['language'] ?? raw['ui_language'] ?? '').toString().trim().toLowerCase();\n    language = rawLanguage.isNotEmpty ? rawLanguage : (locale.toLowerCase().startsWith('ro') || code == 'RO' ? 'ro' : 'en');")
    if 'static bool get isRomanian' not in txt: txt=txt.replace("  static String get currencyInputLabel", "  static bool get isRomanian => language.toLowerCase().startsWith('ro');\n\n  static String get currencyInputLabel")
else:
    txt=txt.replace("    units=(raw['units'] ?? units).toString();", "    units=(raw['units'] ?? raw['unit_system'] ?? units).toString();\n    final rawLanguage=(raw['language'] ?? raw['ui_language'] ?? '').toString().trim().toLowerCase();\n    language=rawLanguage.isNotEmpty?rawLanguage:(locale.toLowerCase().startsWith('ro')||code=='RO'?'ro':'en');")
    if 'static bool get isRomanian' not in txt: txt=txt.replace("  static String money", "  static bool get isRomanian => language.toLowerCase().startsWith('ro');\n\n  static String money")
cc.write_text(txt)

candidates=list((root/'lib/screens').glob('*.dart'))+list((root/'lib/widgets').glob('*.dart'))
state=root/('lib/state/app_session.dart' if name=='driver' else 'lib/state/passenger_session.dart')
if state.exists(): candidates.append(state)
for p in candidates:
    txt=p.read_text(); original=txt
    for en in sorted(translations,key=len,reverse=True):
        if "'" not in en: txt=txt.replace("'"+en+"'", "'"+en+"'.tr")
        if '"' not in en: txt=txt.replace('"'+en+'"', '"'+en+'".tr')
    txt=txt.replace('.tr.tr','.tr')
    if txt!=original:
        txt='\n'.join((line.replace('const ','') if '.tr' in line else line) for line in txt.splitlines())+'\n'
        if 'core/localization.dart' not in txt:
            imports=list(re.finditer(r'^import .*?;\s*$',txt,re.M))
            if imports:
                pos=imports[-1].end(); txt=txt[:pos]+"\nimport '../core/localization.dart';"+txt[pos:]
        p.write_text(txt)

pub=root/'pubspec.yaml'; t=pub.read_text()
app=root/'lib/config/app_config.dart'; a=app.read_text()
if name=='driver':
    t=t.replace('version: 0.6.1+16','version: 0.6.2+17')
    a=a.replace("version = '0.6.1'","version = '0.6.2'")
else:
    t=t.replace('version: 0.5.9+20','version: 0.6.0+21')
    a=a.replace("version = '0.5.9'","version = '0.6.0'")
pub.write_text(t); app.write_text(a)
print(f'Applied automatic localization pack to {name}')
