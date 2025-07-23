/**
 * Debug script to test TypeScript parser directly
 */

const ts = require('typescript');

// Test content from vite.config.ts
const testContent = `import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
})`;

function testParse() {
    console.log('TypeScript version:', ts.version);
    
    try {
        // Create source file with different options
        const sourceFile = ts.createSourceFile(
            'test.ts',
            testContent,
            ts.ScriptTarget.Latest,
            true,
            ts.ScriptKind.TS
        );
        
        console.log('✓ Source file created successfully');
        console.log('Line count:', sourceFile.getLineAndCharacterOfPosition(sourceFile.end).line + 1);
        
        // Try different compiler options
        const compilerOptions = {
            target: ts.ScriptTarget.ES2022,
            module: ts.ModuleKind.ESNext,
            jsx: ts.JsxEmit.React,
            allowJs: true,
            esModuleInterop: true,
            allowSyntheticDefaultImports: true,
            skipLibCheck: true,
            noResolve: true,
            isolatedModules: true
        };
        
        // Create a program without host
        console.log('\nTrying to create program...');
        
        const host = ts.createCompilerHost(compilerOptions);
        host.getSourceFile = (fileName) => {
            if (fileName === 'test.ts') return sourceFile;
            return undefined;
        };
        host.fileExists = () => true;
        host.readFile = () => '';
        host.directoryExists = () => true;
        host.getDirectories = () => [];
        host.resolveModuleNames = () => [];
        
        const program = ts.createProgram(['test.ts'], compilerOptions, host);
        console.log('✓ Program created successfully');
        
        // Get diagnostics
        const syntaxDiagnostics = program.getSyntacticDiagnostics(sourceFile);
        console.log('Syntax diagnostics:', syntaxDiagnostics.length);
        
        // Try to traverse AST
        console.log('\nTraversing AST...');
        let nodeCount = 0;
        
        function visit(node) {
            nodeCount++;
            if (node.kind === ts.SyntaxKind.ImportDeclaration) {
                console.log('Found import:', node.moduleSpecifier?.text);
            }
            ts.forEachChild(node, visit);
        }
        
        visit(sourceFile);
        console.log(`✓ Traversed ${nodeCount} nodes`);
        
    } catch (error) {
        console.error('Error:', error.message);
        console.error('Stack:', error.stack);
    }
}

// Run test
testParse();