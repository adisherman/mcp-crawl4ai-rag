/**
 * Enhanced TypeScript/JavaScript Parser Worker with Usage Pattern Extraction
 * 
 * Extends the base parser to extract usage patterns like:
 * - Method calls (object.method())
 * - Function calls (func())
 * - Property accesses (object.property)
 * - Constructor calls (new Class())
 */

const { parentPort } = require('worker_threads');
const ts = require('typescript');

/**
 * Enhanced AST extractor that extracts both declarations and usage patterns
 */
class EnhancedASTExtractor {
    constructor(sourceFile) {
        this.sourceFile = sourceFile;
        this.result = {
            // Declarations
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
            namespaces: [],
            
            // Usage patterns
            functionCalls: [],
            methodCalls: [],
            propertyAccesses: [],
            constructorCalls: [],
            jsxElements: [],
            typeReferences: []
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
        // Extract declarations (same as before)
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
        
        // Extract usage patterns
        this.extractUsagePatterns(node);
        
        // Recurse through children
        ts.forEachChild(node, child => this.visit(child));
    }
    
    extractUsagePatterns(node) {
        // Extract call expressions
        if (ts.isCallExpression(node)) {
            this.extractCallExpression(node);
        }
        
        // Extract property access expressions
        if (ts.isPropertyAccessExpression(node) && !this.isInsideCallExpression(node)) {
            this.extractPropertyAccess(node);
        }
        
        // Extract new expressions
        if (ts.isNewExpression(node)) {
            this.extractConstructorCall(node);
        }
        
        // Extract JSX elements
        if (ts.isJsxElement(node) || ts.isJsxSelfClosingElement(node)) {
            this.extractJSXElement(node);
        }
        
        // Extract type references
        if (ts.isTypeReferenceNode(node)) {
            this.extractTypeReference(node);
        }
    }
    
    extractCallExpression(node) {
        const expression = node.expression;
        
        if (ts.isPropertyAccessExpression(expression)) {
            // Method call: object.method()
            const object = this.getObjectName(expression.expression);
            const method = expression.name.text;
            const args = this.extractArguments(node.arguments);
            
            this.result.methodCalls.push({
                object: object,
                method: method,
                arguments: args,
                line: this.getLineNumber(node),
                object_type: this.inferObjectType(expression.expression)
            });
        } else if (ts.isIdentifier(expression)) {
            // Function call: func()
            const name = expression.text;
            const args = this.extractArguments(node.arguments);
            
            // Check if it's a React hook
            if (name.startsWith('use')) {
                this.result.hooks.push({
                    name: name,
                    line: this.getLineNumber(node)
                });
            }
            
            this.result.functionCalls.push({
                name: name,
                arguments: args,
                line: this.getLineNumber(node)
            });
        }
    }
    
    extractPropertyAccess(node) {
        const object = this.getObjectName(node.expression);
        const property = node.name.text;
        
        this.result.propertyAccesses.push({
            object: object,
            property: property,
            line: this.getLineNumber(node),
            object_type: this.inferObjectType(node.expression)
        });
    }
    
    extractConstructorCall(node) {
        let className = '';
        
        if (ts.isIdentifier(node.expression)) {
            className = node.expression.text;
        } else if (ts.isPropertyAccessExpression(node.expression)) {
            className = node.expression.getText();
        }
        
        const args = node.arguments ? this.extractArguments(node.arguments) : [];
        
        this.result.constructorCalls.push({
            class: className,
            arguments: args,
            line: this.getLineNumber(node)
        });
    }
    
    extractJSXElement(node) {
        let tagName = '';
        let props = [];
        let selfClosing = false;
        
        if (ts.isJsxElement(node)) {
            tagName = node.openingElement.tagName.getText();
            props = this.extractJSXProps(node.openingElement.attributes);
        } else if (ts.isJsxSelfClosingElement(node)) {
            tagName = node.tagName.getText();
            props = this.extractJSXProps(node.attributes);
            selfClosing = true;
        }
        
        const isCustomComponent = /^[A-Z]/.test(tagName) || tagName.includes('.');
        
        this.result.jsxElements.push({
            tagName: tagName,
            props: props,
            line: this.getLineNumber(node),
            selfClosing: selfClosing,
            isCustomComponent: isCustomComponent
        });
    }
    
    extractTypeReference(node) {
        const typeName = node.typeName.getText();
        
        this.result.typeReferences.push({
            name: typeName,
            line: this.getLineNumber(node)
        });
    }
    
    // Helper methods
    getObjectName(node) {
        if (ts.isIdentifier(node)) {
            return node.text;
        } else if (ts.isPropertyAccessExpression(node)) {
            return this.getObjectName(node.expression) + '.' + node.name.text;
        } else if (ts.isCallExpression(node)) {
            return this.getObjectName(node.expression) + '()';
        } else if (ts.isArrayLiteralExpression(node)) {
            return '[array]';
        } else if (ts.isObjectLiteralExpression(node)) {
            return '{object}';
        } else if (ts.isStringLiteral(node)) {
            return '[string]';
        } else if (ts.isNumericLiteral(node)) {
            return '[number]';
        }
        return node.getText();
    }
    
    inferObjectType(node) {
        // Try to infer the type of the object
        if (ts.isIdentifier(node)) {
            const text = node.text;
            // Check common patterns
            if (text === 'console') return 'Console';
            if (text === 'Math') return 'Math';
            if (text === 'Array') return 'ArrayConstructor';
            if (text === 'Object') return 'ObjectConstructor';
            if (text === 'String') return 'StringConstructor';
            if (text === 'Date') return 'DateConstructor';
            if (text === 'JSON') return 'JSON';
            if (text === 'Promise') return 'PromiseConstructor';
            
            // Check variable name patterns
            if (text.endsWith('Array') || text.endsWith('List')) return 'Array';
            if (text.endsWith('Map')) return 'Map';
            if (text.endsWith('Set')) return 'Set';
            
            return 'unknown';
        } else if (ts.isPropertyAccessExpression(node)) {
            // For chained calls, check the result type
            const propName = node.name.text;
            // Common array-returning methods
            if (['filter', 'map', 'slice', 'concat', 'sort', 'reverse'].includes(propName)) {
                return 'Array';
            }
            return 'unknown';
        } else if (ts.isCallExpression(node)) {
            // Check common function returns
            const expr = node.expression;
            if (ts.isPropertyAccessExpression(expr)) {
                const method = expr.name.text;
                const obj = this.getObjectName(expr.expression);
                
                // Methods that return arrays
                if (['split', 'match'].includes(method) && obj.includes('String')) return 'Array';
                if (['filter', 'map', 'slice', 'concat'].includes(method)) return 'Array';
                
                // Methods that return strings
                if (['join', 'toString', 'toLowerCase', 'toUpperCase'].includes(method)) return 'string';
            }
            return 'unknown';
        } else if (ts.isArrayLiteralExpression(node)) {
            return 'Array';
        } else if (ts.isObjectLiteralExpression(node)) {
            return 'Object';
        } else if (ts.isStringLiteral(node) || ts.isTemplateExpression(node)) {
            return 'string';
        } else if (ts.isNumericLiteral(node)) {
            return 'number';
        } else if (ts.isNewExpression(node)) {
            const className = node.expression.getText();
            if (className === 'Date') return 'Date';
            if (className === 'Map') return 'Map';
            if (className === 'Set') return 'Set';
            if (className === 'Array') return 'Array';
            return className;
        }
        
        return 'unknown';
    }
    
    isInsideCallExpression(node) {
        let parent = node.parent;
        while (parent) {
            if (ts.isCallExpression(parent) && parent.expression === node) {
                return true;
            }
            if (parent === node.parent) {
                break;
            }
            parent = parent.parent;
        }
        return false;
    }
    
    extractArguments(args) {
        return args.map(arg => ({
            type: this.getArgumentType(arg),
            value: arg.getText().substring(0, 50) // Truncate long arguments
        }));
    }
    
    getArgumentType(node) {
        if (ts.isStringLiteral(node)) return 'string';
        if (ts.isNumericLiteral(node)) return 'number';
        if (ts.isIdentifier(node)) return 'identifier';
        if (ts.isObjectLiteralExpression(node)) return 'object';
        if (ts.isArrayLiteralExpression(node)) return 'array';
        if (ts.isArrowFunction(node) || ts.isFunctionExpression(node)) return 'function';
        return 'unknown';
    }
    
    extractJSXProps(attributes) {
        const props = [];
        if (attributes) {
            attributes.properties.forEach(prop => {
                if (ts.isJsxAttribute(prop)) {
                    props.push(prop.name.text);
                }
            });
        }
        return props;
    }
    
    // Declaration extraction methods (from original parser)
    extractImport(node) {
        const moduleSpecifier = node.moduleSpecifier?.text;
        const importClause = node.importClause;
        
        const importInfo = {
            module: moduleSpecifier,
            line: this.getLineNumber(node),
            default: null,
            namespace: null,
            named: []
        };
        
        if (importClause) {
            if (importClause.name) {
                importInfo.default = importClause.name.text;
            }
            
            if (importClause.namedBindings) {
                if (ts.isNamespaceImport(importClause.namedBindings)) {
                    importInfo.namespace = importClause.namedBindings.name.text;
                } else if (ts.isNamedImports(importClause.namedBindings)) {
                    importClause.namedBindings.elements.forEach(element => {
                        importInfo.named.push({
                            name: element.propertyName?.text || element.name.text,
                            alias: element.propertyName ? element.name.text : null
                        });
                    });
                }
            }
        }
        
        this.result.imports.push(importInfo);
    }
    
    extractExport(node) {
        const exportInfo = {
            line: this.getLineNumber(node),
            type: node.kind === ts.SyntaxKind.ExportAssignment ? 'default' : 'named',
            exported: []
        };
        
        if (node.exportClause && ts.isNamedExports(node.exportClause)) {
            node.exportClause.elements.forEach(element => {
                exportInfo.exported.push({
                    name: element.propertyName?.text || element.name.text,
                    alias: element.propertyName ? element.name.text : null
                });
            });
        }
        
        this.result.exports.push(exportInfo);
    }
    
    extractFunction(node) {
        const functionInfo = {
            name: node.name?.text || '<anonymous>',
            line: this.getLineNumber(node),
            async: !!node.modifiers?.some(m => m.kind === ts.SyntaxKind.AsyncKeyword),
            generator: !!node.asteriskToken,
            parameters: this.extractParameters(node.parameters),
            returnType: node.type?.getText(),
            isExported: !!node.modifiers?.some(m => m.kind === ts.SyntaxKind.ExportKeyword),
            isDefault: !!node.modifiers?.some(m => m.kind === ts.SyntaxKind.DefaultKeyword)
        };
        
        // Check if it's a React component
        if (this.isReactComponent(node)) {
            this.extractComponent(node, 'functional');
        } else {
            this.result.functions.push(functionInfo);
        }
    }
    
    extractClass(node) {
        const classInfo = {
            name: node.name?.text || '<anonymous>',
            line: this.getLineNumber(node),
            extends: node.heritageClauses?.find(h => h.token === ts.SyntaxKind.ExtendsKeyword)?.types[0]?.getText(),
            implements: node.heritageClauses?.find(h => h.token === ts.SyntaxKind.ImplementsKeyword)?.types.map(t => t.getText()) || [],
            isExported: !!node.modifiers?.some(m => m.kind === ts.SyntaxKind.ExportKeyword),
            isDefault: !!node.modifiers?.some(m => m.kind === ts.SyntaxKind.DefaultKeyword),
            members: []
        };
        
        // Extract class members
        node.members.forEach(member => {
            if (ts.isMethodDeclaration(member) || ts.isMethodSignature(member)) {
                classInfo.members.push({
                    name: member.name?.getText() || '',
                    type: 'method',
                    visibility: this.getVisibility(member),
                    static: !!member.modifiers?.some(m => m.kind === ts.SyntaxKind.StaticKeyword),
                    async: !!member.modifiers?.some(m => m.kind === ts.SyntaxKind.AsyncKeyword),
                    parameters: this.extractParameters(member.parameters || [])
                });
            } else if (ts.isPropertyDeclaration(member) || ts.isPropertySignature(member)) {
                classInfo.members.push({
                    name: member.name?.getText() || '',
                    type: 'property',
                    visibility: this.getVisibility(member),
                    static: !!member.modifiers?.some(m => m.kind === ts.SyntaxKind.StaticKeyword),
                    readonly: !!member.modifiers?.some(m => m.kind === ts.SyntaxKind.ReadonlyKeyword),
                    propertyType: member.type?.getText()
                });
            }
        });
        
        // Check if it's a React component
        if (classInfo.extends && classInfo.extends.includes('Component')) {
            const componentInfo = {
                name: classInfo.name,
                type: 'class',
                line: classInfo.line,
                isExported: classInfo.isExported,
                isDefault: classInfo.isDefault,
                props: null,
                hooks: []
            };
            this.result.components.push(componentInfo);
        } else {
            this.result.classes.push(classInfo);
        }
    }
    
    extractInterface(node) {
        const interfaceInfo = {
            name: node.name.text,
            line: this.getLineNumber(node),
            extends: node.heritageClauses?.find(h => h.token === ts.SyntaxKind.ExtendsKeyword)?.types.map(t => t.getText()) || [],
            isExported: !!node.modifiers?.some(m => m.kind === ts.SyntaxKind.ExportKeyword),
            properties: []
        };
        
        node.members.forEach(member => {
            if (ts.isPropertySignature(member)) {
                interfaceInfo.properties.push({
                    name: member.name?.getText() || '',
                    type: member.type?.getText(),
                    optional: !!member.questionToken,
                    readonly: !!member.modifiers?.some(m => m.kind === ts.SyntaxKind.ReadonlyKeyword)
                });
            }
        });
        
        this.result.interfaces.push(interfaceInfo);
    }
    
    extractTypeAlias(node) {
        const typeInfo = {
            name: node.name.text,
            line: this.getLineNumber(node),
            type: node.type.getText(),
            isExported: !!node.modifiers?.some(m => m.kind === ts.SyntaxKind.ExportKeyword)
        };
        
        this.result.types.push(typeInfo);
    }
    
    extractEnum(node) {
        const enumInfo = {
            name: node.name.text,
            line: this.getLineNumber(node),
            isExported: !!node.modifiers?.some(m => m.kind === ts.SyntaxKind.ExportKeyword),
            members: []
        };
        
        node.members.forEach(member => {
            enumInfo.members.push({
                name: member.name?.getText() || '',
                value: member.initializer?.getText()
            });
        });
        
        this.result.enums.push(enumInfo);
    }
    
    extractVariableStatement(node) {
        const isExported = !!node.modifiers?.some(m => m.kind === ts.SyntaxKind.ExportKeyword);
        
        node.declarationList.declarations.forEach(decl => {
            // Check if it's a React component
            const componentInfo = this.checkForReactComponent(decl);
            if (componentInfo) {
                this.extractComponentFromVariable(decl, isExported, componentInfo);
            } else {
                const varInfo = {
                    name: decl.name.getText(),
                    line: this.getLineNumber(decl),
                    kind: node.declarationList.flags & ts.NodeFlags.Const ? 'const' : 
                          node.declarationList.flags & ts.NodeFlags.Let ? 'let' : 'var',
                    type: decl.type?.getText(),
                    isExported: isExported
                };
                
                this.result.variables.push(varInfo);
            }
        });
    }
    
    extractNamespace(node) {
        const namespaceInfo = {
            name: node.name.text,
            line: this.getLineNumber(node),
            isExported: !!node.modifiers?.some(m => m.kind === ts.SyntaxKind.ExportKeyword)
        };
        
        this.result.namespaces.push(namespaceInfo);
    }
    
    // React-specific helpers
    isReactComponent(node) {
        if (!node.name) return false;
        
        const name = node.name.text;
        if (!/^[A-Z]/.test(name)) return false;
        
        if (node.parameters.length > 0) {
            const firstParam = node.parameters[0];
            const paramName = firstParam.name?.getText();
            if (paramName === 'props' || (firstParam.type && firstParam.type.getText().includes('Props'))) {
                return true;
            }
        }
        
        return false;
    }
    
    isReactComponentExpression(node) {
        if (ts.isArrowFunction(node) || ts.isFunctionExpression(node)) {
            if (node.parameters.length > 0) {
                const firstParam = node.parameters[0];
                const paramName = firstParam.name?.getText();
                if (paramName === 'props' || (firstParam.type && firstParam.type.getText().includes('Props'))) {
                    return true;
                }
            }
        }
        return false;
    }
    
    extractComponent(node, type) {
        const componentInfo = {
            name: node.name?.text || '<anonymous>',
            type: type,
            line: this.getLineNumber(node),
            isExported: !!node.modifiers?.some(m => m.kind === ts.SyntaxKind.ExportKeyword),
            isDefault: !!node.modifiers?.some(m => m.kind === ts.SyntaxKind.DefaultKeyword),
            props: null,
            hooks: []
        };
        
        if (type === 'functional' && node.parameters.length > 0) {
            const propsParam = node.parameters[0];
            if (propsParam.type) {
                componentInfo.props = propsParam.type.getText();
            }
        }
        
        const hooks = this.findHooks(node.body);
        componentInfo.hooks = hooks;
        
        this.result.components.push(componentInfo);
    }
    
    extractComponentFromVariable(decl, isExported, metadata = {}) {
        const componentInfo = {
            name: decl.name.text,
            type: 'functional',
            line: this.getLineNumber(decl),
            isExported: isExported,
            isDefault: false,
            props: null,
            hooks: [],
            ...metadata
        };
        
        if (decl.type) {
            componentInfo.props = decl.type.getText();
        }
        
        if (decl.initializer) {
            const hooks = this.findHooks(decl.initializer);
            componentInfo.hooks = hooks;
        }
        
        this.result.components.push(componentInfo);
    }
    
    checkForReactComponent(decl) {
        if (!decl.initializer) return null;
        
        const initializer = decl.initializer;
        
        // Check for forwardRef pattern
        if (ts.isCallExpression(initializer)) {
            const expression = initializer.expression;
            
            let isForwardRef = false;
            if (ts.isIdentifier(expression) && expression.text === 'forwardRef') {
                isForwardRef = true;
            } else if (ts.isPropertyAccessExpression(expression)) {
                const name = expression.name.text;
                if (ts.isIdentifier(expression.expression)) {
                    const object = expression.expression.text;
                    if (name === 'forwardRef' && object === 'React') {
                        isForwardRef = true;
                    }
                }
            }
            
            if (isForwardRef) {
                const componentArg = initializer.arguments[0];
                if (componentArg && (ts.isArrowFunction(componentArg) || ts.isFunctionExpression(componentArg))) {
                    return {
                        isForwardRef: true,
                        displayName: this.getDisplayName(decl)
                    };
                }
            }
            
            // Similar checks for memo and other HOCs...
        }
        
        if (this.isReactComponentExpression(initializer)) {
            return {
                displayName: this.getDisplayName(decl)
            };
        }
        
        return null;
    }
    
    getDisplayName(decl) {
        // Simplified version - could be enhanced
        return null;
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
 * Parse TypeScript/JavaScript content with usage pattern extraction
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
    
    // Extract AST information including usage patterns
    const extractor = new EnhancedASTExtractor(sourceFile);
    const result = extractor.extract();
    
    // Add file metadata
    result.filename = filename;
    result.language = getLanguage(filename);
    result.lineCount = sourceFile.getLineAndCharacterOfPosition(sourceFile.end).line + 1;
    
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