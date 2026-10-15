const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const {execFileSync} = require('node:child_process');
const root = path.resolve(__dirname,'..');
const {chromium} = require(path.join(root,'.tools/revision-web/node_modules/playwright'));
const credentials = fs.readFileSync(path.join(root,'.tools/acceso-inicial.txt'),'utf8');
const base = 'http://127.0.0.1:8011';
const report = {comprobaciones:[],documentos:[],erroresJavascript:[]};
let browser;
const check = label => {report.comprobaciones.push(label); console.log(label+': OK');};
(async () => {
    browser = await chromium.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true});
    const page = await browser.newPage({viewport:{width:1440,height:1100}});
    page.on('pageerror', error => report.erroresJavascript.push(error.message));
    await page.goto(base+'/ingresar');
    await page.locator('[name=email]').fill(credentials.match(/Correo: ([^\r\n]+)/)[1]);
    await page.locator('[name=password]').fill(credentials.match(/Contrase[^:]+: ([^\r\n]+)/u)[1]);
    await page.getByRole('button',{name:'Ingresar',exact:true}).click();
    await page.waitForURL('**/documentos');
    assert.equal(await page.locator('#modo_ocr').count(),0);
    check('Carga simplificada sin selector OCR');
    for (const [kind,file,mime] of [
        ['pdf','.tools/ejemplo-digital-bloque3.pdf','application/pdf'],
        ['png','.tools/ocr-bloque4/imagen.png','image/png'],
        ['jpg','.tools/ocr-bloque4/invitacion.jpg','image/jpeg']]) {
        const name = 'prueba-automatico-'+Date.now()+'.'+kind;
        await page.locator('#archivo').setInputFiles({name,mimeType:mime,buffer:fs.readFileSync(path.join(root,file))});
        await Promise.all([page.waitForEvent('load'),page.locator('#upload-button').click()]);
        const row = page.locator('tr[data-uuid]').filter({hasText:name});
        const uuid = await row.getAttribute('data-uuid');
        report.documentos.push({uuid,entrada:kind});
        execFileSync('C:/xampp/php/php.exe',[path.join(root,'.tools/process-automatic-browser.php'),uuid],
            {cwd:root,env:{...process.env,PHP_INI_SCAN_DIR:path.join(root,'config/php')},timeout:180000,stdio:'pipe'});
        await page.waitForFunction(id => !document.querySelector(`tr[data-uuid="${id}"] [data-pdf]`).hidden,uuid,{timeout:15000});
        const response = await page.request.get(base+'/documentos/'+uuid+'/pdf');
        assert.equal(response.status(),200);
        assert.match(response.headers()['content-type'],/application\/pdf/);
        assert.equal((await response.body()).subarray(0,5).toString(),'%PDF-');
        await row.locator('[data-review]').click();
        await page.waitForURL('**/revision');
        const text = await page.locator('#extracted-text').inputValue();
        assert.match(text.toUpperCase(),/IMANTAG/);
        assert.equal(await page.getByRole('link',{name:'Abrir PDF digitalizado',exact:true}).count(),1);
        if (kind === 'pdf') {
            await page.waitForFunction(() => document.getElementById('preview-status').textContent.startsWith('Página'),null,{timeout:30000});
        } else {
            await page.waitForFunction(() => !!document.getElementById('original-image')?.naturalWidth);
        }
        check(kind.toUpperCase()+': carga real, PDF privado, transcripción e integridad');
        if (kind === 'png') await page.screenshot({path:path.join(root,'.tools/automatico-revision.png'),fullPage:true});
        await page.goto(base+'/documentos');
    }
    await page.screenshot({path:path.join(root,'.tools/automatico-listado.png'),fullPage:true});
    assert.deepEqual(report.erroresJavascript,[]);
    check('Sin errores JavaScript');
})().catch(error => {console.error(error); process.exitCode=1;}).finally(async () => {
    fs.writeFileSync(path.join(root,'.tools/automatico-browser-report.json'),JSON.stringify(report,null,2));
    await browser?.close();
});
