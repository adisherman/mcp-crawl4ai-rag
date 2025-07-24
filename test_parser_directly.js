const fs = require('fs');
const http = require('http');

const content = fs.readFileSync('test_typescript_hallucinations.ts', 'utf8');

const data = JSON.stringify({
    content: content,
    filename: 'test_typescript_hallucinations.ts'
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
        console.log('Constructor calls:', result.constructorCalls?.length || 0);
        console.log('Method calls:', result.methodCalls?.length || 0);
        console.log('Function calls:', result.functionCalls?.length || 0);
        
        if (result.methodCalls && result.methodCalls.length > 0) {
            console.log('\nSample method calls:');
            result.methodCalls.slice(0, 3).forEach(m => {
                console.log(`  - ${m.object}.${m.method}()`);
            });
        }
    });
});

req.on('error', error => console.error(error));
req.write(data);
req.end();
