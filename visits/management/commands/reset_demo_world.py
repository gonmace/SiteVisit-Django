"""
reset_demo_world — limpieza total + reseed completo de la demo.

Borra TODOS los datos transaccionales (visitas, fotos, sitios, etc.)
preservando los usuarios. Luego carga 186 sitios reales y siembra visitas
demo con fotos junk descargadas de loremflickr / picsum.

Uso:
    python manage.py reset_demo_world            # pide confirmación
    python manage.py reset_demo_world --yes      # sin confirmación
    python manage.py reset_demo_world --dry-run  # solo log, no modifica nada
    python manage.py reset_demo_world --seed 42  # random seed reproducible
    python manage.py reset_demo_world --skip-wipe
    python manage.py reset_demo_world --skip-sites
    python manage.py reset_demo_world --skip-visits
"""
import random
import shutil
import ssl
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

# Context sin verificacion SSL — aceptable para descargas de imagenes demo
_SSL_CTX = ssl._create_unverified_context()

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from home.models import SiteSetting
from photos.models import Photo
from sites.models import Site
from users.models import ProfilePhoto, User
from visits.models import Visit, VisitPhoto, VisitTrackingPoint

# ── Catálogo de sitios ────────────────────────────────────────────────────────
# (code_pti, operator_code, name, lat, lon)
SITES = [
    ('CL-AT-1108', 'AT10252', 'Puente Nicolasa Freirina',          -28.505028, -70.996028),
    ('CL-AT-1076', 'AT9573',  'Ruta 5 Estacion Travesia',          -27.539750, -70.445694),
    ('CL-AT-1070', 'AT9567',  'Ruta C-17 Juan Godoy',              -27.220806, -70.256110),
    ('CL-AT-1064', 'AT9561',  'Ruta C-13 a Potrerillos',           -26.319444, -69.484806),
    ('CL-AN-1177', 'AN9997',  'Punta Arenas Antofagasta',          -21.637444, -70.139527),
    ('CL-AN-1182', 'AN10005', 'Punta Chileno',                     -21.487917, -70.766110),
    ('CL-AN-1245', 'AN10165', 'Central Tamaya',                    -22.163556, -70.919170),
    ('CL-AT-1056', 'AT9552',  'Ruta 5 Cruce C-13',                 -26.365167, -70.515750),
    ('CL-AN-1118', 'AN9498',  'Estacion Colupito',                  -22.210333, -69.988722),
    ('CL-AN-1121', 'AN9501',  'Ruta 24 Geoglifos',                 -22.266583, -69.431056),
    ('CL-AN-1122', 'AN9502',  'Estacion Cerrillos',                 -22.281333, -69.821500),
    ('CL-AT-1051', 'AT9547',  'Ruta 5 Las Bombas',                 -26.293060, -70.446194),
    ('CL-BI-1301', 'BI8208',  'Reserva Nonguén Sur',               -36.929611, -72.963000),
    ('CL-AN-1164', 'AN9776',  'Quebrada Peineta',                  -25.550833, -70.778330),
    ('CL-AN-1145', 'AN9526',  'Cruce B-70 con B-710',              -24.206778, -70.281722),
    ('CL-ML-1297', 'MA10614', 'RPT El Manzano',                    -35.173361, -72.100830),
    ('CL-AN-1140', 'AN9521',  'Estacion Lacalle',                   -24.545861, -69.795222),
    ('CL-AN-1141', 'AN9522',  'Ruta B-70 Mina La Falsa',           -24.197944, -70.335056),
    ('CL-VS-1333', 'VA8123',  'Cuesta Chacabuco',                  -32.959611, -70.707583),
    ('CL-AN-1225', 'AN10054', 'Ruinas B55 Ruta',                   -24.568890, -69.800944),
    ('CL-AN-1239', 'AN10070', 'Nova Ventura Ruta 1',               -25.107146, -70.497860),
    ('CL-VS-1319', 'VA9919',  'Guardia Vieja Ruta 60H',            -32.899833, -70.234722),
    ('CL-AN-1127', 'AN9507',  'Cerro Gualga',                      -23.740560, -69.593250),
    ('CL-AN-1135', 'AN9515',  'Ruta 5 Gualga Norte',               -22.990361, -69.552972),
    ('CL-AN-1160', 'AN9544',  'Quebrada de la Cachina',            -25.830222, -70.410833),
    ('CL-AN-1161', 'AN9545',  'Quebrada Buena Esperanza',          -25.890583, -70.457861),
    ('CL-AN-1162', 'AN9546',  'Mina Yaquie',                       -25.791000, -70.374778),
    ('CL-VS-1318', 'VA9917',  'El Juncal Ruta 60H',                -32.871361, -70.151694),
    ('CL-AN-1333', 'AN10016', 'Estacion San Pedro Ruta 21',         -21.958472, -68.548250),
    ('CL-AN-1316', 'AN10018', 'Cerro Polapi',                      -21.630611, -68.311972),
    ('CL-AN-1375', 'AN10019', 'Salar de Ascotan',                  -21.533722, -68.363194),
    ('CL-AN-1379', 'AN10022', 'Volcan del Azufre',                 -21.689861, -68.253000),
    ('CL-AN-1346', 'AN10023', 'Parque eolico Valle de los Vientos',-22.541333, -68.800750),
    ('CL-AN-1340', 'AN10031', 'Laguna Negra Ruta 27',              -23.195861, -67.360139),
    ('CL-AN-1319', 'AN10038', 'Chile-Argentina',                   -23.820694, -67.318250),
    ('CL-AN-1356', 'AN10040', 'Quebrada Nacimiento',               -23.665361, -67.835222),
    ('CL-AN-1374', 'AN10041', 'Salar Aguas Calientes-V. Miñiques', -23.891750, -67.726250),
    ('CL-AN-1328', 'AN10048', 'Estacion Augusta Victoria',          -24.111555, -69.336638),
    ('CL-AN-1317', 'AN10053', 'Cerro Punta Gruesa',                -24.403028, -68.348583),
    ('CL-AN-1347', 'AN10062', 'Peninsula Cangrejos',               -24.374750, -70.550639),
    ('CL-AN-1338', 'AN10096', 'Interseccion Ruta 1',               -25.503361, -70.415556),
    ('CL-AN-1363', 'AN10603', 'RPT El Cobre',                      -24.294806, -70.518111),
    ('CL-AN-1361', 'AN11690', 'RPT Oficina Cota',                  -24.816660, -69.877111),
    ('CL-AN-1359', 'AN11691', 'RPT La Taira',                      -21.845916, -68.638861),
    ('CL-AN-1365', 'AN9495',  'Ruta 24 Estacion Quillagua',        -22.908330, -70.130222),
    ('CL-AN-1334', 'AN9505',  'Estacion Teresa',                    -21.971000, -69.586889),
    ('CL-AN-1377', 'AN9509',  'Tranque Sloman',                    -21.816000, -69.537806),
    ('CL-AN-1310', 'AN9523',  'Camino Caleta El Cobre',            -24.256389, -70.417944),
    ('CL-AN-1367', 'AN9525',  'Ruta 5 Norte Tetillas',             -24.263194, -70.356940),
    ('CL-AN-1314', 'AN9534',  'Cerro Buenos Aires',                -24.734806, -69.759806),
    ('CL-AN-1366', 'AN9539',  'Ruta 5 Mina Tropezon',              -25.556417, -70.161611),
    ('CL-AN-1350', 'AN9999',  'Punta Aña',                         -22.188610, -70.185778),
    ('CL-CO-1296', 'CO10084', 'Huanta Ruta 41',                    -29.871444, -70.327389),
    ('CL-CO-1299', 'CO11686', 'RPT Vista Hermosa',                 -30.162694, -70.751670),
    ('CL-CO-1302', 'CO9819',  'Ruta D-895 3',                      -31.446916, -71.205444),
    ('CL-AN-1348', 'AN10015', 'Planta El Abra',                    -22.100528, -68.596111),
    ('CL-AN-1324', 'AN10039', 'Cuesta Barros Aranas',              -22.704500, -68.440861),
    ('CL-AN-1312', 'AN10052', 'Campamento B55',                    -24.244444, -68.499972),
    ('CL-AN-1353', 'AN10060', 'Punta Moreno El Cobre',             -24.270222, -70.520444),
    ('CL-AN-1358', 'AN10596', 'RPT Cerro El Viento',               -24.693694, -69.992944),
    ('CL-AN-1329', 'AN9497',  'Estacion Barriles',                  -22.117444, -70.914440),
    ('CL-AN-1343', 'AN9520',  'Oficina Rosario',                   -24.355111, -69.942722),
    ('CL-AN-1369', 'AN9531',  'Ruta B-710 Paranal',                -24.645944, -70.369167),
    ('CL-AT-1150', 'AT2174',  'Flamenco',                          -26.590806, -70.694861),
    ('CL-AT-1160', 'AT9566',  'Ruta C-17 Mina Dulcinea',           -27.112333, -69.972556),
    ('CL-CO-1297', 'CO10098', 'Presa Embalse la Laguna',           -30.203444, -70.432780),
    ('CL-CO-1301', 'CO9623',  'Ruta 5 Punta Palmeras',             -31.228889, -71.589306),
    ('CL-AN-1307', 'AN9496',  'Acceso Oriente Tocopilla',          -22.851940, -70.160056),
    ('CL-AN-1372', 'AN9524',  'Ruta B-70 Mina Encalada',           -24.310750, -70.462278),
    ('CL-AN-1309', 'AN9998',  'Cabo Paquica',                      -21.901750, -70.181583),
    ('CL-AP-1076', 'AP9456',  'Acha',                              -18.590778, -70.250722),
    ('CL-AP-1077', 'AP9954',  'Altos de Copaquilla',               -18.404528, -69.641472),
    ('CL-AN-1355', 'TA9490',  'Quebrada Mal Paso',                 -21.413750, -69.495083),
    ('CL-CO-1295', 'CO10088', 'Cerro Ruta 41 Nor Oriente',         -29.958000, -70.179194),
    ('CL-TP-1147', 'TA9716',  'Altos de Pica',                     -20.372278, -69.413610),
    ('CL-CO-1298', 'CO10086', 'Punet Balala Ruta 41',              -29.920611, -70.296611),
    ('CL-AN-1352', 'AN10006', 'Punta del Urcu',                    -21.763611, -70.151778),
    ('CL-AN-1351', 'AN10009', 'Punta Cobija',                      -22.560444, -70.260861),
    ('CL-AN-1368', 'AN1747',  'Ruta Antofagasta - Taltal 3',       -25.854170, -69.820917),
    ('CL-AN-1313', 'AN5756',  'Cerro Barriles',                    -22.171083, -70.147528),
    ('CL-AI-1079', 'AY9444',  'Ruta X-50 Puente Mañihuales',       -45.304222, -72.337333),
    ('CL-MA-1532', 'MG9939',  'Morro Chico Natales',               -52.231390, -71.671111),
    ('CL-AN-1362', 'AN10598', 'RPT Sierra Esmeralda',              -25.908278, -70.466306),
    ('CL-CO-1300', 'CO10080', 'Ruta 41 Juntas del Toro',           -29.950389, -70.147417),
    ('CL-LL-1239', 'LL9934',  'Mirador Isla Marimeli',             -41.698694, -72.464917),
    ('CL-RM-2225', 'RM9599',  'El Volcan SJ de Maipo',             -33.805056, -70.256778),
    ('CL-VS-1467', 'VA9411',  'Cordillera El Melon',               -32.720694, -71.467780),
    ('CL-MA-1533', 'MG10113', 'Villa Tehuelches',                  -52.375611, -71.482056),
    ('CL-MA-1529', 'MG9946',  'Lago Cabeza de Mar',                -52.746083, -71.227220),
    ('CL-MA-1527', 'MG10114', 'Cerro Guido',                       -50.909278, -72.489000),
    ('CL-AN-1380', 'AN10034', 'Volcan Miñiques Ruta 23',           -23.838833, -67.829500),
    ('CL-AN-1357', 'AN10028', 'Roca Purico',                       -22.918556, -67.731222),
    ('CL-AN-1339', 'AN10036', 'Laguna de Tuyato',                  -23.891500, -67.521778),
    ('CL-AN-1373', 'AN10035', 'Salar de Aguas Calientes',          -23.917583, -67.661083),
    ('CL-AN-1315', 'AN10020', 'Cerro Carasilia',                   -21.734778, -68.279833),
    ('CL-AN-1308', 'AN9540',  'Aerodromo Las Breas',               -25.546000, -70.316667),
    ('CL-AN-1332', 'AN10017', 'Estacion Polapi',                    -21.797556, -68.412333),
    ('CL-AN-1349', 'AN10000', 'Planta Punta Blanca',               -22.147806, -70.217417),
    ('CL-AP-1078', 'AP9956',  'Camino desbarrancado Ruta 11',      -18.269889, -69.565556),
    ('CL-RM-2224', 'RM3807',  'Cuesta a Maitenes',                 -33.532361, -70.241472),
    ('CL-TP-1149', 'TA9985',  'Carcanal de Napa',                  -20.525417, -68.789306),
    ('CL-TP-1152', 'TA9471',  'Quebrada de Chiza',                 -19.204306, -70.921110),
    ('CL-TP-1148', 'TA9982',  'Campamento pampa Llacho',           -19.837639, -68.759056),
    ('CL-TP-1158', 'TA9990',  'Volcan Michincha',                  -20.927667, -68.571722),
    ('CL-TP-1151', 'TA9493',  'Estacion Hilaricos',                 -21.540722, -69.524500),
    ('CL-TP-1156', 'TA9491',  'Ruta A-685 Tambillo',               -20.477333, -69.209139),
    ('CL-TP-1150', 'TA9484',  'Cruce Ruta A-633 Ruta A-651',       -20.263028, -69.440278),
    ('CL-TP-1154', 'TA9483',  'Ruta A-651 Tasma',                  -20.267083, -69.359167),
    ('CL-TP-1155', 'TA9486',  'Ruta A-685 Altos de Pica',          -20.392139, -69.985280),
    ('CL-TP-1153', 'TA9479',  'Ruta A-651 Tambillos',              -20.280667, -69.258667),
    ('CL-TP-1157', 'TA9989',  'Salar de Michincha',                -20.976194, -68.533444),
    ('CL-AN-1335', 'AN10049', 'Estacion Varillas-Minera Escondida', -24.232944, -69.178722),
    ('CL-AN-1364', 'AN9499',  'Ruta 24 Cerro Abra',                -22.268694, -69.274556),
    ('CL-AN-1318', 'AN10043', 'Cerros de la Pacana',               -23.119111, -67.475222),
    ('CL-AN-1337', 'AN2799',  'Hornitos',                          -22.920589, -70.297611),
    ('CL-AN-1360', 'AN11689', 'RPT Llullaillaco',                  -24.268500, -68.556277),
    ('CL-AN-1306', 'AN9537',  'Acceso Mina Julia',                 -24.840833, -69.899389),
    ('CL-AN-1336', 'AN10021', 'Faldeos del Azufre',                -21.758417, -68.350639),
    ('CL-AP-1079', 'AP9463',  'Codpa',                             -18.828556, -69.747972),
    ('CL-AP-1080', 'AP9464',  'Ofragia',                           -18.830417, -69.779778),
    ('CL-AN-1133', 'AN9513',  'Oficina Concepcion',                -23.175000, -69.401056),
    ('CL-AN-1120', 'AN9500',  'Ruta 24 Desvio Chung Chung',        -22.290028, -69.094583),
    ('CL-AN-1130', 'AN9510',  'Oficina Santa Ana',                 -22.136139, -69.571333),
    ('CL-CO-1133', 'CO4216',  'Andacollo Mineros',                 -30.204417, -71.937060),
    ('CL-AN-1325', 'AN10025', 'Cuesta Cerro Carolina',             -22.843278, -68.325944),
    ('CL-AN-1226', 'AN10055', 'Estacion Alcalde Poblete',           -24.136333, -69.173861),
    ('CL-CO-1262', 'CO11685', 'RPT Aguas del Volcán',              -29.987889, -70.752780),
    ('CL-AN-1344', 'AN9535',  'Pampa Cachina',                     -25.732472, -70.366250),
    ('CL-CO-1179', 'CO10081', 'Nueva Elqui Ruta 41',               -30.668610, -70.954720),
    ('CL-TP-1049', 'TA9476',  'Ruta 5 Norte Rosita',               -19.844389, -69.800750),
    ('CL-ML-1348', 'MA8228',  'Estero Iloca Cerro',                -34.942667, -72.152528),
    ('CL-CO-1194', 'CO10102', 'Ruta 41 Cerro Piedra Roja',         -30.222972, -69.921722),
    ('CL-CO-1196', 'CO10104', 'Cumbre Gabriela Mistral',           -30.175278, -69.834861),
    ('CL-CO-1141', 'CO9608',  'Ruta 5 Punta El Viento',            -29.663278, -71.303833),
    ('CL-AT-1047', 'AT4516',  'Caleta del Obispo',                 -26.698889, -70.736389),
    ('CL-AN-1311', 'AN10027', 'Camino del Cajon',                  -22.919361, -68.406670),
    ('CL-AN-1370', 'AN10045', 'Ruta B55',                          -24.106917, -70.111056),
    ('CL-AN-1331', 'AN10050', 'Estacion Imilac',                    -24.223306, -68.894472),
    ('CL-AN-1321', 'AN10056', 'Cristales de Laja',                 -24.132472, -68.737278),
    ('CL-AN-1371', 'AN10057', 'Ruta B-55 Antofagasta - Socompa',   -24.294083, -68.478167),
    ('CL-AN-1376', 'AN10058', 'Salar de Imilac',                   -24.214167, -68.797472),
    ('CL-AN-1327', 'AN10059', 'Estacion Adolfo Zaldivar',           -24.200839, -69.983430),
    ('CL-AN-1378', 'AN2160',  'Valle de la Luna Repetidor',         -22.749139, -68.404444),
    ('CL-AN-1354', 'AN9518',  'Quebrada de Mateo',                 -23.931000, -70.294527),
    ('CL-AT-1110', 'AT9554',  'Ruta C-13 a LLanta',                -26.353806, -69.910583),
    ('CL-AT-1052', 'AT9548',  'Ruta 5 Quebrada Pan de Azucar',     -26.108111, -70.443556),
    ('CL-MA-1528', 'MG9452',  'Estancia Alejandra',                -52.457258, -69.807950),
    ('CL-MA-1530', 'MG9938',  'Lago Diana',                        -51.916361, -72.971940),
    ('CL-MA-1534', 'MG9940',  'Potrero Estancia El Arroyo',        -52.211500, -71.331250),
    ('CL-MA-1531', 'MG9945',  'Laguna de los Palos Norte',         -52.700000, -71.883330),
    ('CL-AT-1161', 'AT9565',  'Ruta C-17 Portezuelo Chimbero',     -26.934611, -69.917944),
    ('CL-RM-2226', 'RM10180', 'Sendero Cerro La Cruz Peñalolen',   -33.451389, -70.507861),
    ('CL-AN-1323', 'AN9504',  'Cruce Las Torres',                  -22.278306, -69.667972),
    ('CL-AN-1341', 'AN9519',  'Mano del Desierto',                 -24.181417, -70.139694),
    ('CL-AN-1320', 'AN1133',  'Chiu Chiu',                         -22.304031, -68.638834),
    ('CL-AN-1322', 'AN10051', 'Cruce B241',                        -24.753060, -68.605083),
    ('CL-AN-1330', 'AN10073', 'Estacion Breas',                     -25.487889, -70.434972),
    ('CL-AN-1342', 'AN9538',  'Oficina Britania',                  -25.314139, -69.861500),
    ('CL-AN-1345', 'AN9508',  'Pampa Limon Verde',                 -22.574750, -69.244720),
    ('CL-AN-1326', 'AN9506',  'Desvio Oficina Algorta',            -22.873111, -69.592528),
    ('CL-AT-1155', 'AT9824',  'Ruta 5 Los Medanos',                -26.469056, -70.685694),
    ('CL-AT-1157', 'AT9571',  'Ruta 5 Zoologico de Piedra',        -26.943388, -70.788083),
    ('CL-AT-1149', 'AT9555',  'Estacion Llanta',                    -26.326393, -69.824368),
    ('CL-AT-1151', 'AT9536',  'Ruta 5 Campamento Santa Marta',     -25.988694, -70.434917),
    ('CL-AT-1158', 'AT9823',  'Ruta C-13 Mina Candelaria',         -26.335556, -69.699361),
    ('CL-AT-1152', 'AT9807',  'Ruta 5 Cardones - Copiapo',         -27.449611, -70.368639),
    ('CL-AT-1156', 'AT9708',  'Ruta 5 Portezuelo Aris',            -28.805889, -70.794750),
    ('CL-AT-1154', 'AT9585',  'Ruta 5 Desvio Viscachitas',         -28.764639, -70.776806),
    ('CL-AT-1153', 'AT9572',  'Ruta 5 Cruce Bahia Inglesa',        -27.180167, -70.790472),
    ('CL-AT-1159', 'AT9568',  'Ruta C-17 Estacion Chimbero',       -26.872306, -69.915167),
    ('CL-AN-1382', 'AN10004', 'Puerto Coloso',                     -23.777889, -70.484472),
    ('CL-AT-1164', 'AT9551',  'Ruta 5 Cruce C-203',                -26.335452, -70.580737),
    ('CL-TP-1161', 'TA9475',  'Cuesta de Chiza',                   -19.291833, -69.889250),
    ('CL-TP-1162', 'TA9480',  'Ruta A-651 Alca',                   -20.284944, -69.808890),
    ('CL-AN-1383', 'AN0156',  'Minera Escondida Despacho',          -24.347916, -69.303570),
    ('CL-TP-1163', 'TA9473',  'Quebrada de Tana',                  -19.458306, -69.975639),
    ('CL-AT-1165', 'AT9570',  'Ruta 5 Punta Caleuche',             -26.394972, -70.686000),
    ('CL-TP-1164', 'TA9489',  'Cerro Soledad',                     -21.234167, -69.546250),
    ('CL-TP-1165', 'TA9655',  'Ruta A-75 a Pica',                  -20.558556, -69.457861),
    ('CL-TP-1166', 'TA9472',  'Chiza',                             -19.211306, -69.968389),
    ('CL-TP-1167', 'TA9469',  'Cuesta Camarones',                  -19.103222, -70.503060),
    ('CL-AN-1384', 'AN10029', 'Camino Cerro Toco',                 -22.922167, -67.854306),
    ('CL-AN-1385', 'AN10037', 'Volcan El Laco',                    -23.846472, -67.458388),
    ('CL-AN-1386', 'AN10042', 'Cerro Toco Norte',                  -22.918472, -67.787778),
    ('CL-TP-1168', 'TA9981',  'Portezuelo Picavilque',             -19.761056, -68.777444),
    ('CL-TP-1169', 'TA9979',  'Camino Ancuaque',                   -19.551028, -68.733889),
]

REASONS = [
    'Mantención preventiva antenas',
    'Cambio de ODU por falla reportada',
    'Ajuste de azimut y tilt',
    'Revisión de sistema de energía',
    'Instalación de nueva ODU 4G/5G',
    'Inspección post tormenta eléctrica',
    'Actualización de firmware RRU',
    'Reparación de líneas de transmisión',
    'Revisión de sistema de cooling',
    'Cambio de baterías banco de energía',
    'Instalación de equipo microonda',
    'Mantención correctiva por alarma NOC',
    'Reposición combustible generador',
    'Revisión sistema HVAC shelter',
    'Verificación alarma BTS NOC',
]

# Fotos que se crean para visitas en estado TRABAJANDO
WORKING_PHOTO_TYPES = [
    'llegada',
    'vehiculo',
    'encargado',
    'trabajo_1',
    'trabajo_2',
]

PHOTO_TAG_MAP = {
    'llegada':   'tower,antenna,telecom',
    'vehiculo':  'pickup,truck,van',
    'encargado': 'engineer,worker,helmet',
    'trabajo_1': 'cable,industrial,electricity',
    'trabajo_2': 'equipment,network,telecom',
}

# Pool de 10 estados por tecnico: se mezcla y trunca a n (3-8)
STATUS_POOL = (
    [Visit.Status.COMPLETADA]           * 2 +
    [Visit.Status.TRABAJANDO]           * 2 +
    [Visit.Status.PENDIENTE_APROBACION] * 3 +
    [Visit.Status.PROGRAMADA]           * 2 +
    [Visit.Status.CANCELADA]            * 1
)


def _jitter(scale: float = 0.0005) -> float:
    return random.uniform(-scale, scale)


def _make_route(site_lat: float, site_lon: float, n: int = 5):
    start_lat = site_lat + random.uniform(0.015, 0.035) * random.choice([-1, 1])
    start_lon = site_lon + random.uniform(0.015, 0.035) * random.choice([-1, 1])
    pts = []
    for i in range(n):
        f = i / (n - 1)
        lat = start_lat + (site_lat - start_lat) * f + _jitter(0.0005)
        lon = start_lon + (site_lon - start_lon) * f + _jitter(0.0005)
        pts.append((lat, lon))
    pts[-1] = (site_lat + _jitter(0.00004), site_lon + _jitter(0.00004))
    return pts


class Command(BaseCommand):
    help = 'Reset completo del mundo demo: borra, carga sitios reales y siembra visitas+fotos.'

    def add_arguments(self, parser):
        parser.add_argument('--yes', action='store_true', help='Sin confirmación interactiva.')
        parser.add_argument('--dry-run', action='store_true', help='Solo muestra lo que haría.')
        parser.add_argument('--seed', type=int, default=42, help='Semilla aleatoria (default 42).')
        parser.add_argument('--skip-wipe',   action='store_true')
        parser.add_argument('--skip-sites',  action='store_true')
        parser.add_argument('--skip-visits', action='store_true')

    def handle(self, *args, **options):
        random.seed(options['seed'])
        self._dry = options['dry_run']

        if self._dry:
            self.stdout.write(self.style.WARNING('>> DRY-RUN - no se modificara nada.'))

        if not options['yes'] and not self._dry:
            self._confirm()

        self.stdout.write('=== Reset demo world ===')

        if not options['skip_wipe']:
            self._wipe()
        if not options['skip_sites']:
            self._load_sites()
        if not options['skip_visits']:
            self._seed_visits()

        self.stdout.write(self.style.SUCCESS('\nOK Completado.'))

    # ── Confirmación ──────────────────────────────────────────────────────────

    def _confirm(self):
        visits  = Visit.objects.count()
        sites   = Site.objects.count()
        photos  = VisitPhoto.objects.count()
        users   = User.objects.count()
        self.stdout.write('━━━ Este comando borrará ━━━')
        self.stdout.write(f'  Visitas:         {visits}')
        self.stdout.write(f'  Fotos de visita: {photos}')
        self.stdout.write(f'  Sitios:          {sites}')
        self.stdout.write(f'  Usuarios:        {users} (NO se tocarán)')
        self.stdout.write('')
        ans = input('¿Continuar? Esta acción no se puede deshacer. [s/N]: ').strip().lower()
        if ans not in ('s', 'si', 'sí', 'y', 'yes'):
            self.stdout.write('  Cancelado.')
            raise SystemExit(0)

    # ── Wipe ──────────────────────────────────────────────────────────────────

    def _wipe(self):
        self.stdout.write('\n>> Borrando datos transaccionales...')
        if self._dry:
            self.stdout.write('  (dry-run: skip)')
            return

        with transaction.atomic():
            tp,  _ = VisitTrackingPoint.objects.all().delete()
            vp,  _ = VisitPhoto.objects.all().delete()
            v,   _ = Visit.objects.all().delete()
            pp,  _ = ProfilePhoto.objects.all().delete()
            ph,  _ = Photo.objects.all().delete()
            ss,  _ = SiteSetting.objects.all().delete()
            s,   _ = Site.objects.all().delete()

        self.stdout.write(
            f'  {v} visitas - {vp} fotos - {tp} tracking - '
            f'{pp} profile photos - {ph} photos genericos - '
            f'{ss} site settings - {s} sitios eliminados.'
        )

        media = Path(settings.MEDIA_ROOT)
        for subdir in ('visits', 'profile_photos', 'photos'):
            target = media / subdir
            if target.exists():
                shutil.rmtree(target)
            target.mkdir(parents=True, exist_ok=True)
        self.stdout.write('  Directorios media limpiados.')

    # ── Sitios ────────────────────────────────────────────────────────────────

    def _load_sites(self):
        self.stdout.write('\n>> Cargando sitios...')
        if self._dry:
            self.stdout.write(f'  (dry-run: cargaría {len(SITES)} sitios con company=pti)')
            return

        heights = [24, 30, 36, 42, 48]
        created = updated = 0
        for code, op_code, name, lat, lon in SITES:
            _, c = Site.objects.update_or_create(
                code=code,
                defaults=dict(
                    operator_code=op_code,
                    name=name,
                    latitude=lat,
                    longitude=lon,
                    height=random.choice(heights),
                    company=User.Company.PTI,
                    is_active=True,
                ),
            )
            if c:
                created += 1
            else:
                updated += 1

        self.stdout.write(f'  {created} creados, {updated} actualizados.')

    # ── Visitas + fotos ───────────────────────────────────────────────────────

    def _seed_visits(self):
        self.stdout.write('\n>> Sembrando visitas...')

        techs = list(User.objects.filter(
            role=User.Role.TECHNICIAN,
            is_active=True,
        ))
        if not techs:
            self.stdout.write('  ! Sin técnicos activos. Ejecuta create_test_users primero.')
            return

        coordinators = list(User.objects.filter(role=User.Role.MANAGER))
        approvers    = list(User.objects.filter(
            role__in=[User.Role.MANAGER, User.Role.SUPER_MANAGER],
        ))
        sites = list(Site.objects.filter(is_active=True))
        if not sites:
            self.stdout.write('  ! Sin sitios. Ejecuta primero sin --skip-sites.')
            return

        today = timezone.localdate()

        if self._dry:
            total_visits = sum(random.randint(3, 8) for _ in techs)
            self.stdout.write(
                f'  (dry-run: ~{total_visits} visitas para {len(techs)} técnicos, '
                f'{len(sites)} sitios disponibles)'
            )
            return

        # Pre-descarga el pool de imágenes (25 descargas)
        image_pool = self._build_image_pool()

        total_visits = total_photos = 0

        for tech in techs:
            n = random.randint(3, 8)
            pool = STATUS_POOL[:]
            random.shuffle(pool)
            statuses = pool[:n]

            for status in statuses:
                site       = random.choice(sites)
                coord      = random.choice(coordinators) if coordinators else None
                approver   = random.choice(approvers)    if approvers    else None
                sched_date = self._sched_date(today, status)

                visit_kwargs = dict(
                    technician    = tech,
                    site          = site,
                    coordinator   = coord,
                    status        = status,
                    reason        = random.choice(REASONS),
                    scheduled_date= sched_date,
                    eta           = self._random_eta(),
                    notas         = '[JUNK] demo seeded',
                )

                if status == Visit.Status.PROGRAMADA:
                    visit_kwargs['approved_by'] = approver
                    visit_kwargs['approved_at'] = timezone.now() - timedelta(
                        hours=random.randint(2, 72)
                    )

                if status in (Visit.Status.TRABAJANDO, Visit.Status.COMPLETADA):
                    t_start = datetime.combine(
                        sched_date,
                        datetime.min.time(),
                    ).replace(
                        hour=random.randint(7, 10),
                        minute=random.randint(0, 45),
                        tzinfo=timezone.get_current_timezone(),
                    )
                    visit_kwargs['approved_by']          = approver
                    visit_kwargs['approved_at']          = t_start - timedelta(hours=random.randint(2, 24))
                    visit_kwargs['hora_inicio_trabajos'] = t_start
                    if status == Visit.Status.COMPLETADA:
                        duration = timedelta(minutes=random.randint(60, 180))
                        visit_kwargs['hora_fin_trabajos'] = t_start + duration

                if status == Visit.Status.CANCELADA:
                    visit_kwargs['notas'] = '[JUNK] Cancelado por solicitud operaciones.'

                v = Visit.objects.create(**visit_kwargs)
                total_visits += 1

                if status in (Visit.Status.TRABAJANDO, Visit.Status.COMPLETADA):
                    total_photos += self._create_photos(v, site, image_pool)
                    self._create_tracking(v, site, visit_kwargs['hora_inicio_trabajos'])

        self.stdout.write(
            f'  {total_visits} visitas creadas - {total_photos} fotos sembradas.'
        )

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _sched_date(today, status):
        if status == Visit.Status.PROGRAMADA:
            return today + timedelta(days=random.randint(1, 14))
        if status == Visit.Status.CANCELADA:
            return today - timedelta(days=random.randint(1, 30))
        if status == Visit.Status.COMPLETADA:
            return today - timedelta(days=random.randint(1, 30))
        if status == Visit.Status.TRABAJANDO:
            return today
        # PENDIENTE_APROBACION
        return today - timedelta(days=random.randint(0, 7))

    @staticmethod
    def _random_eta():
        from datetime import time as _time
        h = random.randint(7, 17)
        m = random.choice([0, 15, 30, 45])
        return _time(h, m)

    def _create_photos(self, visit: Visit, site: Site, pool: dict) -> int:
        count = 0
        t_base = visit.hora_inicio_trabajos or timezone.now()
        for i, pt in enumerate(WORKING_PHOTO_TYPES):
            images = pool.get(pt)
            if not images:
                continue
            data  = random.choice(images)
            taken = t_base + timedelta(minutes=random.randint(5, 60) * (i + 1))
            VisitPhoto.objects.create(
                visit       = visit,
                photo_type  = pt,
                image       = ContentFile(data, name=f'junk_{visit.id}_{pt}.jpg'),
                description = f'[JUNK] {pt}',
                latitude    = site.latitude  + _jitter(),
                longitude   = site.longitude + _jitter(),
                taken_at    = taken,
            )
            count += 1
        return count

    @staticmethod
    def _create_tracking(visit: Visit, site: Site, t_start: datetime):
        route  = _make_route(site.latitude, site.longitude, 5)
        events = ['salida', 'llegada', 'inicio', 'finalizado', 'cierre']
        offsets = [0.0, 0.25, 0.30, 0.90, 1.0]
        duration = timedelta(minutes=random.randint(60, 180))
        total_s  = duration.total_seconds()
        for event, (lat, lon), frac in zip(events, route, offsets):
            VisitTrackingPoint.objects.create(
                visit     = visit,
                event     = event,
                latitude  = lat,
                longitude = lon,
                timestamp = t_start + timedelta(seconds=total_s * frac),
            )

    # ── Descarga de imágenes ──────────────────────────────────────────────────

    def _build_image_pool(self, pool_size: int = 5) -> dict:
        self.stdout.write('  Descargando pool de imagenes...')
        pool = {}
        for i, pt in enumerate(WORKING_PHOTO_TYPES):
            tags   = PHOTO_TAG_MAP.get(pt, 'industrial')
            images = []
            for j in range(pool_size):
                seed = i * 100 + j + 1
                try:
                    data = self._fetch_image(tags, seed)
                    images.append(data)
                    self.stdout.write(f'  OK {pt}/{j+1}', ending='\r')
                except Exception as exc:
                    self.stdout.write(self.style.WARNING(f'  ! {pt}/{seed}: {exc}'))
            pool[pt] = images or None
        self.stdout.write('  Pool listo.          ')
        return pool

    @staticmethod
    def _fetch_image(tags: str, seed: int) -> bytes:
        headers = {'User-Agent': 'Mozilla/5.0 (SiteVisit-Demo/1.0)'}
        # loremflickr — imagenes reales con lock reproducible
        url = f'https://loremflickr.com/640/480/{tags}?lock={seed}'
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=8, context=_SSL_CTX) as r:
                return r.read()
        except Exception:
            pass
        # fallback: picsum con seed numerico
        url = f'https://picsum.photos/seed/{seed}/800/600'
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=8, context=_SSL_CTX) as r:
            return r.read()
