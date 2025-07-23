/**
 * Fixed TypeScript/JavaScript Parser Worker
 * 
 * Uses TypeScript Compiler API for parsing without full program creation
 * to avoid module resolution issues.
 */

const { parentPort } = require('worker_threads');
const ts = require('typescript');

/**
 * AST extractor that works with just a source file
 */
class ASTExtractor {
    constructor(sourceFile) {
        this.sourceFile = sourceFile;
        this.result = {
            imports: [],
            exports: [],
            functions: [],
            classes: [],
            interfaces: [],
            types: [],
            enums: [],
            components: [],
            hooks: [],
            variables: [],
            namespaces: []
        };
    }
    
    extract() {
        this.visit(this.sourceFile);
        return this.result;
    }
    
    getLineNumber(node) {
        const { line } = this.sourceFile.getLineAndCharacterOfPosition(node.getStart());
        return line + 1;
    }
    
    visit(node) {
        switch (node.kind) {
            case ts.SyntaxKind.ImportDeclaration:
                this.extractImport(node);
                break;
                
            case ts.SyntaxKind.ExportDeclaration:
            case ts.SyntaxKind.ExportAssignment:
                this.extractExport(node);
                break;
                
            case ts.SyntaxKind.FunctionDeclaration:
                this.extractFunction(node);
                break;
                
            case ts.SyntaxKind.ClassDeclaration:
                this.extractClass(node);
                break;
                
            case ts.SyntaxKind.InterfaceDeclaration:
                this.extractInterface(node);
                break;
                
            case ts.SyntaxKind.TypeAliasDeclaration:
                this.extractTypeAlias(node);
                break;
                
            case ts.SyntaxKind.EnumDeclaration:
                this.extractEnum(node);
                break;
                
            case ts.SyntaxKind.VariableStatement:
                this.extractVariableStatement(node);
                break;
                
            case ts.SyntaxKind.ModuleDeclaration:
                this.extractNamespace(node);
                break;
        }
        
        ts.forEachChild(node, child => this.visit(child));
    }
    
    extractImport(node) {
        const moduleSpecifier = node.moduleSpecifier?.text;
        const importClause = node.importClause;
        
        const importInfo = {
            module: moduleSpecifier,
            line: this.getLineNumber(node),
            isTypeOnly: node.isTypeOnly || false
        };
        
        if (importClause) {
            // Default import
            if (importClause.name) {
                importInfo.default = importClause.name.text;
            }
            
            // Named imports
            if (importClause.namedBindings) {
                if (ts.isNamespaceImport(importClause.namedBindings)) {
                    importInfo.namespace = importClause.namedBindings.name.text;
                } else if (ts.isNamedImports(importClause.namedBindings)) {
                    importInfo.named = importClause.namedBindings.elements.map(e => ({
                        name: e.name.text,
                        alias: e.propertyName?.text
                    }));
                }
            }
        }
        
        this.result.imports.push(importInfo);
    }
    
    extractExport(node) {
        const exportInfo = {
            line: this.getLineNumber(node),
            isTypeOnly: node.isTypeOnly || false
        };
        
        if (node.kind === ts.SyntaxKind.ExportAssignment) {
            exportInfo.default = true;
            exportInfo.expression = node.expression.getText();
        } else if (node.exportClause) {
            if (ts.isNamedExports(node.exportClause)) {
                exportInfo.named = node.exportClause.elements.map(e => ({
                    name: e.name.text,
                    alias: e.propertyName?.text
                }));
            }
        }
        
        if (node.moduleSpecifier) {
            exportInfo.from = node.moduleSpecifier.text;
        }
        
        this.result.exports.push(exportInfo);
    }
    
    extractFunction(node) {
        if (!node.name) return;
        
        const funcInfo = {
            name: node.name.text,
            line: this.getLineNumber(node),
            isAsync: !!node.modifiers?.some(m => m.kind === ts.SyntaxKind.AsyncKeyword),
            isExported: !!node.modifiers?.some(m => m.kind === ts.SyntaxKind.ExportKeyword),
            isDefault: !!node.modifiers?.some(m => m.kind === ts.SyntaxKind.DefaultKeyword),
            parameters: this.extractParameters(node.parameters),
            returnType: node.type?.getText()
        };
        
        // Check if it's a React component
        if (this.isReactComponent(node)) {
            this.extractComponent(node, 'functional');
        } else {
            this.result.functions.push(funcInfo);
        }
    }
    
    extractClass(node) {
        if (!node.name) return;
        
        const classInfo = {
            name: node.name.text,
            line: this.getLineNumber(node),
            isExported: !!node.modifiers?.some(m => m.kind === ts.SyntaxKind.ExportKeyword),
            isDefault: !!node.modifiers?.some(m => m.kind === ts.SyntaxKind.DefaultKeyword),
            isAbstract: !!node.modifiers?.some(m => m.kind === ts.SyntaxKind.AbstractKeyword),
            extends: node.heritageClauses?.find(h => h.token === ts.SyntaxKind.ExtendsKeyword)
                ?.types[0]?.expression?.getText(),
            implements: node.heritageClauses?.find(h => h.token === ts.SyntaxKind.ImplementsKeyword)
                ?.types.map(t => t.expression.getText()) || [],
            members: []
        };
        
        // Extract class members
        node.members.forEach(member => {
            if (ts.isMethodDeclaration(member) && member.name) {
                classInfo.members.push({
                    type: 'method',
                    name: member.name.getText(),
                    visibility: this.getVisibility(member),
                    isStatic: !!member.modifiers?.some(m => m.kind === ts.SyntaxKind.StaticKeyword),
                    isAsync: !!member.modifiers?.some(m => m.kind === ts.SyntaxKind.AsyncKeyword),
                    parameters: this.extractParameters(member.parameters),
                    returnType: member.type?.getText()
                });
            } else if (ts.isPropertyDeclaration(member) && member.name) {
                classInfo.members.push({
                    type: 'property',
                    name: member.name.getText(),
                    visibility: this.getVisibility(member),
                    isStatic: !!member.modifiers?.some(m => m.kind === ts.SyntaxKind.StaticKeyword),
                    isReadonly: !!member.modifiers?.some(m => m.kind === ts.SyntaxKind.ReadonlyKeyword),
                    propertyType: member.type?.getText()  // Use propertyType to avoid overwriting type: 'property'
                });
            }
        });
        
        // Check if it's a React class component
        if (this.isReactClassComponent(node)) {
            this.extractComponent(node, 'class');
        } else {
            this.result.classes.push(classInfo);
        }
    }
    
    extractInterface(node) {
        if (!node.name) return;
        
        const interfaceInfo = {
            name: node.name.text,
            line: this.getLineNumber(node),
            isExported: !!node.modifiers?.some(m => m.kind === ts.SyntaxKind.ExportKeyword),
            extends: node.heritageClauses?.find(h => h.token === ts.SyntaxKind.ExtendsKeyword)
                ?.types.map(t => t.expression.getText()) || [],
            properties: [],
            methods: []
        };
        
        // Extract interface members
        node.members.forEach(member => {
            if (ts.isPropertySignature(member) && member.name) {
                interfaceInfo.properties.push({
                    name: member.name.getText(),
                    type: member.type?.getText(),
                    optional: !!member.questionToken
                });
            } else if (ts.isMethodSignature(member) && member.name) {
                interfaceInfo.methods.push({
                    name: member.name.getText(),
                    parameters: this.extractParameters(member.parameters),
                    returnType: member.type?.getText()
                });
            }
        });
        
        this.result.interfaces.push(interfaceInfo);
    }
    
    extractTypeAlias(node) {
        if (!node.name) return;
        
        this.result.types.push({
            name: node.name.text,
            line: this.getLineNumber(node),
            isExported: !!node.modifiers?.some(m => m.kind === ts.SyntaxKind.ExportKeyword),
            type: node.type.getText()
        });
    }
    
    extractEnum(node) {
        if (!node.name) return;
        
        this.result.enums.push({
            name: node.name.text,
            line: this.getLineNumber(node),
            isExported: !!node.modifiers?.some(m => m.kind === ts.SyntaxKind.ExportKeyword),
            members: node.members.map(m => m.name.getText())
        });
    }
    
    extractVariableStatement(node) {
        const isExported = !!node.modifiers?.some(m => m.kind === ts.SyntaxKind.ExportKeyword);
        
        node.declarationList.declarations.forEach(decl => {
            if (decl.name && ts.isIdentifier(decl.name)) {
                const varInfo = {
                    name: decl.name.text,
                    line: this.getLineNumber(decl),
                    isExported: isExported,
                    isConst: node.declarationList.flags & ts.NodeFlags.Const,
                    type: decl.type?.getText()
                };
                
                // Check if it's a React component
                if (decl.initializer && this.isReactComponentExpression(decl.initializer)) {
                    this.extractComponentFromVariable(decl, isExported);
                } else {
                    this.result.variables.push(varInfo);
                }
            }
        });
    }
    
    extractNamespace(node) {
        if (!node.name) return;
        
        this.result.namespaces.push({
            name: node.name.text,
            line: this.getLineNumber(node),
            isExported: !!node.modifiers?.some(m => m.kind === ts.SyntaxKind.ExportKeyword)
        });
    }
    
    extractComponent(node, type) {
        const name = node.name?.text || 'Anonymous';
        
        const componentInfo = {
            name: name,
            type: type,
            line: this.getLineNumber(node),
            isExported: !!node.modifiers?.some(m => m.kind === ts.SyntaxKind.ExportKeyword),
            isDefault: !!node.modifiers?.some(m => m.kind === ts.SyntaxKind.DefaultKeyword),
            props: null,
            hooks: []
        };
        
        // Extract props type
        if (type === 'functional' && node.parameters.length > 0) {
            const propsParam = node.parameters[0];
            if (propsParam.type) {
                componentInfo.props = propsParam.type.getText();
            }
        }
        
        // Extract hooks usage
        const hooks = this.findHooks(node.body);
        componentInfo.hooks = hooks;
        
        this.result.components.push(componentInfo);
    }
    
    extractComponentFromVariable(decl, isExported) {
        const componentInfo = {
            name: decl.name.text,
            type: 'functional',
            line: this.getLineNumber(decl),
            isExported: isExported,
            isDefault: false,
            props: null,
            hooks: []
        };
        
        // Try to extract props type
        if (decl.type) {
            componentInfo.props = decl.type.getText();
        }
        
        // Extract hooks from the component body
        if (decl.initializer) {
            const hooks = this.findHooks(decl.initializer);
            componentInfo.hooks = hooks;
        }
        
        this.result.components.push(componentInfo);
    }
    
    isReactComponent(node) {
        // Check if function returns JSX or has FC/Component type annotation
        const name = node.name?.text || '';
        return /^[A-Z]/.test(name) || 
               (node.type && node.type.getText().includes('React.')) ||
               this.hasJSXReturn(node.body);
    }
    
    isReactClassComponent(node) {
        return node.heritageClauses?.some(h => 
            h.token === ts.SyntaxKind.ExtendsKeyword &&
            h.types.some(t => {
                const text = t.expression.getText();
                return text.includes('Component') || text.includes('PureComponent');
            })
        );
    }
    
    isReactComponentExpression(node) {
        // Check for arrow functions or function expressions that might be components
        if (ts.isArrowFunction(node) || ts.isFunctionExpression(node)) {
            return this.hasJSXReturn(node.body);
        }
        return false;
    }
    
    hasJSXReturn(node) {
        if (!node) return false;
        
        let hasJSX = false;
        
        const checkNode = (n) => {
            if (ts.isJsxElement(n) || ts.isJsxSelfClosingElement(n) || ts.isJsxFragment(n)) {
                hasJSX = true;
            }
            if (!hasJSX) {
                ts.forEachChild(n, checkNode);
            }
        };
        
        checkNode(node);
        return hasJSX;
    }
    
    findHooks(node) {
        const hooks = [];
        
        const findHookCalls = (n) => {
            if (ts.isCallExpression(n) && n.expression) {
                const callName = n.expression.getText();
                if (callName.startsWith('use')) {
                    hooks.push({
                        name: callName,
                        line: this.getLineNumber(n)
                    });
                }
            }
            ts.forEachChild(n, findHookCalls);
        };
        
        if (node) {
            findHookCalls(node);
        }
        
        return hooks;
    }
    
    extractParameters(parameters) {
        return parameters.map(param => ({
            name: param.name?.getText() || '',
            type: param.type?.getText(),
            optional: !!param.questionToken,
            hasDefault: !!param.initializer
        }));
    }
    
    getVisibility(member) {
        if (member.modifiers) {
            if (member.modifiers.some(m => m.kind === ts.SyntaxKind.PrivateKeyword)) return 'private';
            if (member.modifiers.some(m => m.kind === ts.SyntaxKind.ProtectedKeyword)) return 'protected';
        }
        return 'public';
    }
}

/**
 * Get the appropriate script kind for a filename
 */
function getScriptKind(filename) {
    const ext = filename.toLowerCase();
    if (ext.endsWith('.tsx')) return ts.ScriptKind.TSX;
    if (ext.endsWith('.ts')) return ts.ScriptKind.TS;
    if (ext.endsWith('.jsx')) return ts.ScriptKind.JSX;
    return ts.ScriptKind.JS;
}

/**
 * Get the language from filename
 */
function getLanguage(filename) {
    const ext = filename.toLowerCase();
    if (ext.endsWith('.ts') || ext.endsWith('.tsx')) {
        return 'typescript';
    }
    return 'javascript';
}

/**
 * Parse TypeScript/JavaScript content without creating a full program
 */
function parseContent(content, filename) {
    // Create a source file
    const sourceFile = ts.createSourceFile(
        filename,
        content,
        ts.ScriptTarget.Latest,
        true, // setParentNodes
        getScriptKind(filename)
    );
    
    // Extract AST information without type checking
    const extractor = new ASTExtractor(sourceFile);
    const result = extractor.extract();
    
    // Add file metadata
    result.filename = filename;
    result.language = getLanguage(filename);
    result.lineCount = sourceFile.getLineAndCharacterOfPosition(sourceFile.end).line + 1;
    
    // Note: We skip syntax error checking to avoid needing a full program
    // The AST extraction will still work for files with resolvable syntax
    
    return result;
}

// Listen for parse requests from main thread
parentPort.on('message', ({ content, filename, options }) => {
    try {
        const result = parseContent(content, filename);
        parentPort.postMessage(result);
    } catch (error) {
        parentPort.postMessage({
            error: error.message,
            stack: error.stack,
            filename
        });
    }
});