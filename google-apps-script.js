const SPREADSHEET_ID = 'ENGANXA_AQUÍ_L_ID_DEL_TEU_GOOGLE_SHEETS';
const SHEET_NAME     = 'Leads Interpesca';

const HEADERS = [
  'Data i hora',
  'Nom',
  'Empresa',
  'Telèfon',
  'Email',
  'Tipus negoci',
  'Missatge',
];

// Formulari web → GET amb paràmetres a la URL
function doGet(e) {
  try {
    const data = e.parameter;
    registraLead(data);
    return ContentService
      .createTextOutput('ok')
      .setMimeType(ContentService.MimeType.TEXT);
  } catch (err) {
    console.error('Error a doGet:', err.toString());
    return ContentService
      .createTextOutput('error: ' + err.toString())
      .setMimeType(ContentService.MimeType.TEXT);
  }
}

function registraLead(data) {
  const ss    = SpreadsheetApp.openById(SPREADSHEET_ID);
  let   sheet = ss.getSheetByName(SHEET_NAME);

  if (!sheet) {
    sheet = ss.insertSheet(SHEET_NAME);
  }

  if (sheet.getLastRow() === 0) {
    const headerRow = sheet.getRange(1, 1, 1, HEADERS.length);
    headerRow.setValues([HEADERS]);
    headerRow.setFontWeight('bold');
    headerRow.setBackground('#052830');
    headerRow.setFontColor('#ffffff');
    sheet.setFrozenRows(1);
    sheet.setColumnWidth(1, 160);
    sheet.setColumnWidth(7, 320);
  }

  const tipusMap = {
    restauracio:   'Restauració',
    hotel:         'Hotel',
    collectivitat: 'Col·lectivitat',
    comerc:        'Comerç',
    altres:        'Altres',
  };

  const dataHora = Utilities.formatDate(new Date(), 'Europe/Andorra', 'dd/MM/yyyy HH:mm:ss');

  sheet.appendRow([
    dataHora,
    data.nom      || '',
    data.empresa  || '',
    data.telefon  || '',
    data.email    || '',
    tipusMap[data.tipus] || data.tipus || '',
    data.missatge || '',
  ]);

  const lastRow = sheet.getLastRow();
  if (lastRow % 2 === 0) {
    sheet.getRange(lastRow, 1, 1, HEADERS.length).setBackground('#eef5f7');
  }
}

// Prova des de l'editor: Executar > doTest
function doTest() {
  registraLead({
    nom:      'Prova Manual',
    empresa:  'Restaurant Test',
    telefon:  '+376 123456',
    email:    'prova@test.com',
    tipus:    'restauracio',
    missatge: 'Prova des de l\'editor.',
  });
  console.log('Lead registrat!');
}
