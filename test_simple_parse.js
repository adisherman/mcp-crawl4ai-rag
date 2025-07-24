const code = `
function test() {
  const obj = new MyClass();
  obj.method();
  someFunction();
}
`;

const http = require('http');
const data = JSON.stringify({
    content: code,
    filename: 'test.ts'
});

const options = {
    hostname: 'localhost',
    port: 3456,
    path: '/parse-file',
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
        'Content-Length': data.length
    }
};

const req = http.request(options, res => {
    let body = '';
    res.on('data', chunk => body += chunk);
    res.on('end', () => {
        const result = JSON.parse(body);
        console.log(JSON.stringify(result, null, 2));
    });
});

req.on('error', error => console.error(error));
req.write(data);
req.end();
