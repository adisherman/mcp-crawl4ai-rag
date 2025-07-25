#!/usr/bin/env node

const axios = require('axios');
const fs = require('fs').promises;
const path = require('path');

async function testParser() {
    try {
        // Check if parser service is running
        const healthCheck = await axios.get('http://localhost:3456/health').catch(err => {
            console.error('Parser service not running. Start it with: node typescript_parser_service.js');
            process.exit(1);
        });
        
        console.log('Parser service status:', healthCheck.data);
        
        // Read the test file
        const testFile = path.join(__dirname, '../test_validation/correct_page_component.tsx');
        const content = await fs.readFile(testFile, 'utf8');
        
        console.log('\n=== Testing parser with correct_page_component.tsx ===');
        console.log('File size:', content.length, 'bytes');
        console.log('First 200 chars:', content.substring(0, 200));
        
        // Send to parser
        const response = await axios.post('http://localhost:3456/parse-file', {
            content: content,
            filename: 'correct_page_component.tsx'
        });
        
        const result = response.data;
        
        // Log results
        console.log('\n=== Parser Results ===');
        console.log('Language:', result.language);
        console.log('Line count:', result.lineCount);
        console.log('\nExtracted entities:');
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
        
        // Show details of components
        if (result.components && result.components.length > 0) {
            console.log('\n=== Component Details ===');
            result.components.forEach(comp => {
                console.log(`\nComponent: ${comp.name}`);
                console.log('  Type:', comp.type);
                console.log('  Line:', comp.line);
                console.log('  Exported:', comp.isExported);
                console.log('  Default:', comp.isDefault);
                console.log('  Props:', comp.props);
                console.log('  Hooks:', comp.hooks?.length || 0);
            });
        }
        
        // Show some imports
        if (result.imports && result.imports.length > 0) {
            console.log('\n=== First 5 Imports ===');
            result.imports.slice(0, 5).forEach(imp => {
                console.log(`Line ${imp.line}: import`, 
                    imp.default ? imp.default : '',
                    imp.named ? `{ ${imp.named.map(n => n.name).join(', ')} }` : '',
                    'from', `'${imp.module}'`);
            });
        }
        
        // Save full results for inspection
        const outputFile = path.join(__dirname, 'parser_test_output.json');
        await fs.writeFile(outputFile, JSON.stringify(result, null, 2));
        console.log(`\nFull results saved to: ${outputFile}`);
        
    } catch (error) {
        console.error('\nError testing parser:', error.message);
        if (error.response) {
            console.error('Response status:', error.response.status);
            console.error('Response data:', error.response.data);
        }
    }
}

testParser();