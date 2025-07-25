#!/usr/bin/env node

const { Worker } = require('worker_threads');
const fs = require('fs').promises;
const path = require('path');

async function testParserWorker() {
    try {
        // Read the test file
        const testFile = path.join(__dirname, '../test_validation/correct_page_component.tsx');
        const content = await fs.readFile(testFile, 'utf8');
        
        console.log('\n=== Testing parser worker directly ===');
        console.log('File: correct_page_component.tsx');
        console.log('File size:', content.length, 'bytes');
        
        // Test with parser_worker_usage.js (the one being used)
        console.log('\n--- Testing parser_worker_usage.js ---');
        await testWorker('./parser_worker_usage.js', content, 'correct_page_component.tsx');
        
        // Test with parser_worker_fixed.js for comparison
        console.log('\n--- Testing parser_worker_fixed.js ---');
        await testWorker('./parser_worker_fixed.js', content, 'correct_page_component.tsx');
        
    } catch (error) {
        console.error('\nError:', error.message);
        console.error(error.stack);
    }
}

async function testWorker(workerPath, content, filename) {
    return new Promise((resolve, reject) => {
        const worker = new Worker(path.join(__dirname, workerPath));
        
        worker.on('message', (result) => {
            if (result.error) {
                console.error('Worker error:', result.error);
                console.error('Stack:', result.stack);
            } else {
                console.log('\nParser Results:');
                console.log('- Language:', result.language);
                console.log('- Line count:', result.lineCount);
                console.log('- Imports:', result.imports?.length || 0);
                console.log('- Exports:', result.exports?.length || 0);
                console.log('- Functions:', result.functions?.length || 0);
                console.log('- Classes:', result.classes?.length || 0);
                console.log('- Interfaces:', result.interfaces?.length || 0);
                console.log('- Types:', result.types?.length || 0);
                console.log('- Components:', result.components?.length || 0);
                console.log('- Variables:', result.variables?.length || 0);
                console.log('- Hooks:', result.hooks?.length || 0);
                console.log('- JSX Elements:', result.jsxElements?.length || 0);
                console.log('- Method Calls:', result.methodCalls?.length || 0);
                console.log('- Function Calls:', result.functionCalls?.length || 0);
                
                // Show component details
                if (result.components && result.components.length > 0) {
                    console.log('\nComponents found:');
                    result.components.forEach(comp => {
                        console.log(`  - ${comp.name} (${comp.type}) at line ${comp.line}`);
                    });
                }
                
                // Save results
                const outputFile = path.join(__dirname, `parser_${path.basename(workerPath, '.js')}_output.json`);
                fs.writeFile(outputFile, JSON.stringify(result, null, 2))
                    .then(() => console.log(`\nResults saved to: ${outputFile}`))
                    .catch(err => console.error('Failed to save results:', err));
            }
            
            worker.terminate();
            resolve();
        });
        
        worker.on('error', (error) => {
            console.error('Worker thread error:', error);
            reject(error);
        });
        
        // Send the parse request
        worker.postMessage({ content, filename, options: {} });
    });
}

testParserWorker();