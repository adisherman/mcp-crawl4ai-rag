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
            namespaces: [],
            jsxElements: [],
            methodCalls: [],
            functionCalls: [],
            propertyAccesses: [],
            constructorCalls: []
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
                // Also check if it's a default export of a HOC component
                if (node.kind === ts.SyntaxKind.ExportAssignment && node.expression) {
                    this.checkDefaultExportComponent(node);
                }
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
                
            case ts.SyntaxKind.JsxElement:
            case ts.SyntaxKind.JsxSelfClosingElement:
                this.extractJSXElement(node);
                break;
                
            case ts.SyntaxKind.CallExpression:
                this.extractCallExpression(node);
                break;
                
            case ts.SyntaxKind.PropertyAccessExpression:
                this.extractPropertyAccess(node);
                break;
                
            case ts.SyntaxKind.NewExpression:
                this.extractNewExpression(node);
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
        const baseInfo = {
            line: this.getLineNumber(node),
            isTypeOnly: node.isTypeOnly || false
        };
        
        if (node.kind === ts.SyntaxKind.ExportAssignment) {
            // export default X
            const exportInfo = { ...baseInfo };
            exportInfo.default = true;
            exportInfo.expression = node.expression.getText();
            this.result.exports.push(exportInfo);
        } else if (node.exportClause) {
            if (ts.isNamedExports(node.exportClause)) {
                // For named exports, create individual export entries
                node.exportClause.elements.forEach(e => {
                    const exportInfo = { ...baseInfo };
                    
                    // Handle: export { X as Y } from 'Z'
                    if (e.propertyName) {
                        exportInfo.name = e.propertyName.text;
                        exportInfo.as = e.name.text;
                    } else {
                        // Handle: export { X } from 'Y'
                        exportInfo.name = e.name.text;
                    }
                    
                    if (node.moduleSpecifier) {
                        exportInfo.from = node.moduleSpecifier.text;
                    }
                    
                    this.result.exports.push(exportInfo);
                });
            }
        } else if (node.moduleSpecifier) {
            // export * from 'X'
            const exportInfo = { ...baseInfo };
            exportInfo.from = node.moduleSpecifier.text;
            exportInfo.all = true;
            this.result.exports.push(exportInfo);
        }
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
                    type: decl.type?.getText(),
                    initializer: null,  // Will be populated if needed
                    inferredType: null  // Will be populated based on initializer
                };
                
                // Check if the variable is assigned a function (arrow function or function expression)
                if (decl.initializer) {
                    if (ts.isArrowFunction(decl.initializer) || ts.isFunctionExpression(decl.initializer)) {
                        // Check if it's a React component first
                        const componentInfo = this.checkForReactComponent(decl);
                        if (componentInfo) {
                            this.extractComponentFromVariable(decl, isExported, componentInfo);
                        } else {
                            // It's a regular function, add it to functions list
                            const funcInfo = {
                                name: decl.name.text,
                                line: this.getLineNumber(decl),
                                isAsync: !!decl.initializer.modifiers?.some(m => m.kind === ts.SyntaxKind.AsyncKeyword),
                                isExported: isExported,
                                isArrowFunction: ts.isArrowFunction(decl.initializer),
                                parameters: this.extractParameters(decl.initializer.parameters),
                                returnType: decl.initializer.type?.getText() || decl.type?.getText()
                            };
                            this.result.functions.push(funcInfo);
                        }
                    } else {
                        // Check if it's a React component (including HOC patterns)
                        const componentInfo = this.checkForReactComponent(decl);
                        if (componentInfo) {
                            this.extractComponentFromVariable(decl, isExported, componentInfo);
                        } else {
                            // Enhance variable info with initializer details
                            this.enhanceVariableInfo(varInfo, decl.initializer);
                            this.result.variables.push(varInfo);
                        }
                    }
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
    
    extractJSXElement(node) {
        let tagName;
        let props = [];
        let selfClosing = false;
        let line;
        
        if (ts.isJsxSelfClosingElement(node)) {
            selfClosing = true;
            tagName = node.tagName.getText();
            line = this.getLineNumber(node);
            
            // Extract props from attributes
            if (node.attributes && node.attributes.properties) {
                props = this.extractJSXProps(node.attributes.properties);
            }
        } else if (ts.isJsxElement(node)) {
            tagName = node.openingElement.tagName.getText();
            line = this.getLineNumber(node.openingElement);
            
            // Extract props from opening element attributes
            if (node.openingElement.attributes && node.openingElement.attributes.properties) {
                props = this.extractJSXProps(node.openingElement.attributes.properties);
            }
        }
        
        if (tagName) {
            // Determine if it's a custom component (starts with uppercase) or HTML element
            const isCustomComponent = /^[A-Z]/.test(tagName);
            
            this.result.jsxElements.push({
                tagName: tagName,
                props: props,
                line: line,
                selfClosing: selfClosing,
                isCustomComponent: isCustomComponent
            });
        }
    }
    
    extractJSXProps(properties) {
        const props = [];
        
        properties.forEach(prop => {
            if (ts.isJsxAttribute(prop) && prop.name) {
                const propName = prop.name.text;
                props.push(propName);
            } else if (ts.isJsxSpreadAttribute(prop)) {
                // Handle spread props like {...props}
                props.push({
                    type: 'spread',
                    expression: prop.expression.getText()
                });
            }
        });
        
        return props;
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
    
    extractComponentFromVariable(decl, isExported, metadata = {}) {
        const componentInfo = {
            name: decl.name.text,
            type: 'functional',
            line: this.getLineNumber(decl),
            isExported: isExported,
            isDefault: false,
            props: null,
            hooks: [],
            ...metadata // Include HOC metadata like isForwardRef, isMemo, etc.
        };
        
        // Try to extract props type
        if (decl.type) {
            const typeText = decl.type.getText();
            componentInfo.typeAnnotation = typeText;
            
            // Extract props type from React.FC<Props> or React.FunctionComponent<Props>
            const propsMatch = typeText.match(/^(React\.)?(FC|FunctionComponent)<(.+)>$/);
            if (propsMatch) {
                componentInfo.props = propsMatch[3];
            }
        }
        
        // Extract hooks from the component body
        if (decl.initializer) {
            const hooks = this.findHooks(decl.initializer);
            componentInfo.hooks = hooks;
        }
        
        this.result.components.push(componentInfo);
    }
    
    checkForReactComponent(decl) {
        // First check if the variable has a React component type annotation
        if (decl.type) {
            const typeText = decl.type.getText();
            // Check for React.FC, React.FunctionComponent, FC, FunctionComponent patterns
            // Also handle imported aliases and namespace imports
            if (typeText.match(/^([\w.]+\.)?(FC|FunctionComponent)(<.*>)?$/) ||
                typeText.includes('React.FC') || 
                typeText.includes('React.FunctionComponent')) {
                return {
                    isTypedComponent: true,
                    componentType: typeText,
                    displayName: this.getDisplayName(decl)
                };
            }
        }
        
        if (!decl.initializer) return null;
        
        const initializer = decl.initializer;
        
        // Check for forwardRef pattern
        if (ts.isCallExpression(initializer)) {
            const expression = initializer.expression;
            
            // Handle forwardRef patterns with or without generics
            let isForwardRef = false;
            
            // Check if it's a direct identifier (forwardRef)
            if (ts.isIdentifier(expression) && expression.text === 'forwardRef') {
                isForwardRef = true;
            }
            // Check if it's a property access (React.forwardRef)
            else if (ts.isPropertyAccessExpression(expression)) {
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
            
            // Handle memo patterns
            let isMemo = false;
            
            // Check for memo with same logic as forwardRef
            if (ts.isIdentifier(expression) && expression.text === 'memo') {
                isMemo = true;
            } else if (ts.isPropertyAccessExpression(expression)) {
                const name = expression.name.text;
                const object = expression.expression.getText();
                if (name === 'memo' && object === 'React') {
                    isMemo = true;
                }
            }
            
            if (isMemo) {
                const componentArg = initializer.arguments[0];
                
                // Check for nested forwardRef inside memo
                if (componentArg && ts.isCallExpression(componentArg)) {
                    const innerExpr = componentArg.expression;
                    let isInnerForwardRef = false;
                    
                    // Same checks for forwardRef
                    if (ts.isIdentifier(innerExpr) && innerExpr.text === 'forwardRef') {
                        isInnerForwardRef = true;
                    } else if (ts.isPropertyAccessExpression(innerExpr)) {
                        const name = innerExpr.name.text;
                        if (ts.isIdentifier(innerExpr.expression)) {
                            const object = innerExpr.expression.text;
                            if (name === 'forwardRef' && object === 'React') {
                                isInnerForwardRef = true;
                            }
                        }
                    }
                    
                    if (isInnerForwardRef) {
                        return {
                            isMemo: true,
                            isForwardRef: true,
                            displayName: this.getDisplayName(decl)
                        };
                    }
                }
                
                // Regular memo component
                if (componentArg && (ts.isArrowFunction(componentArg) || 
                    ts.isFunctionExpression(componentArg) || 
                    ts.isIdentifier(componentArg))) {
                    return {
                        isMemo: true,
                        displayName: this.getDisplayName(decl)
                    };
                }
            }
            
            // Handle other HOC patterns (e.g., styled-components, withRouter, etc.)
            const hocExpressionText = expression.getText();
            if (/^with[A-Z]/.test(hocExpressionText) || hocExpressionText.includes('styled.')) {
                return {
                    isHOC: true,
                    hocType: hocExpressionText,
                    displayName: this.getDisplayName(decl)
                };
            }
        }
        
        // Check for regular React component patterns
        if (this.isReactComponentExpression(initializer)) {
            return {
                displayName: this.getDisplayName(decl)
            };
        }
        
        return null;
    }
    
    getDisplayName(decl) {
        // Check if there's a displayName assignment after the declaration
        const parent = decl.parent?.parent; // VariableStatement
        if (parent && parent.parent) {
            const siblings = parent.parent.statements;
            const declIndex = siblings.indexOf(parent);
            
            // Look for displayName assignment in the next few statements
            for (let i = declIndex + 1; i < Math.min(declIndex + 3, siblings.length); i++) {
                const stmt = siblings[i];
                if (ts.isExpressionStatement(stmt) && 
                    ts.isBinaryExpression(stmt.expression) &&
                    stmt.expression.operatorToken.kind === ts.SyntaxKind.EqualsToken) {
                    
                    const left = stmt.expression.left;
                    if (ts.isPropertyAccessExpression(left) &&
                        left.expression.getText() === decl.name.text &&
                        left.name.text === 'displayName') {
                        
                        const right = stmt.expression.right;
                        if (ts.isStringLiteral(right)) {
                            return right.text;
                        }
                    }
                }
            }
        }
        
        return null;
    }
    
    checkDefaultExportComponent(node) {
        const expression = node.expression;
        
        if (ts.isCallExpression(expression)) {
            const callExpr = expression.expression;
            let isForwardRef = false;
            
            // Handle default export forwardRef with generics
            if (ts.isIdentifier(callExpr) && callExpr.text === 'forwardRef') {
                isForwardRef = true;
            } else if (ts.isPropertyAccessExpression(callExpr)) {
                const name = callExpr.name.text;
                if (ts.isIdentifier(callExpr.expression)) {
                    const object = callExpr.expression.text;
                    if (name === 'forwardRef' && object === 'React') {
                        isForwardRef = true;
                    }
                }
            }
            
            if (isForwardRef) {
                const componentArg = expression.arguments[0];
                if (componentArg) {
                    this.result.components.push({
                        name: 'default',
                        type: 'functional',
                        line: this.getLineNumber(node),
                        isExported: true,
                        isDefault: true,
                        isForwardRef: true,
                        props: null,
                        hooks: this.findHooks(componentArg)
                    });
                }
            }
            
            // Handle default export memo
            let isMemo = false;
            
            if (ts.isIdentifier(callExpr) && callExpr.text === 'memo') {
                isMemo = true;
            } else if (ts.isPropertyAccessExpression(callExpr)) {
                const name = callExpr.name.text;
                const object = callExpr.expression.getText();
                if (name === 'memo' && object === 'React') {
                    isMemo = true;
                }
            }
            
            if (isMemo) {
                const componentArg = expression.arguments[0];
                
                // Check for nested forwardRef
                if (componentArg && ts.isCallExpression(componentArg)) {
                    const innerExpr = componentArg.expression;
                    let isInnerForwardRef = false;
                    
                    if (ts.isIdentifier(innerExpr) && innerExpr.text === 'forwardRef') {
                        isInnerForwardRef = true;
                    } else if (ts.isPropertyAccessExpression(innerExpr)) {
                        const name = innerExpr.name.text;
                        if (ts.isIdentifier(innerExpr.expression)) {
                            const object = innerExpr.expression.text;
                            if (name === 'forwardRef' && object === 'React') {
                                isInnerForwardRef = true;
                            }
                        }
                    }
                    
                    if (isInnerForwardRef) {
                        this.result.components.push({
                            name: 'default',
                            type: 'functional',
                            line: this.getLineNumber(node),
                            isExported: true,
                            isDefault: true,
                            isMemo: true,
                            isForwardRef: true,
                            props: null,
                            hooks: this.findHooks(componentArg.arguments[0])
                        });
                        return;
                    }
                }
                
                if (componentArg) {
                    this.result.components.push({
                        name: 'default',
                        type: 'functional',
                        line: this.getLineNumber(node),
                        isExported: true,
                        isDefault: true,
                        isMemo: true,
                        props: null,
                        hooks: this.findHooks(componentArg)
                    });
                }
            }
        }
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
    
    extractCallExpression(node) {
        const expression = node.expression;
        const line = this.getLineNumber(node);
        
        // Extract arguments
        const args = node.arguments?.map(arg => {
            // Try to get a simple representation of the argument
            if (ts.isStringLiteral(arg)) {
                return { type: 'string', value: arg.text };
            } else if (ts.isNumericLiteral(arg)) {
                return { type: 'number', value: arg.text };
            } else if (ts.isIdentifier(arg)) {
                return { type: 'identifier', value: arg.text };
            } else {
                return { type: 'expression', value: arg.getText().substring(0, 50) }; // Truncate long expressions
            }
        }) || [];
        
        // Check if it's a method call (object.method())
        if (ts.isPropertyAccessExpression(expression)) {
            const object = expression.expression.getText();
            const method = expression.name.text;
            
            this.result.methodCalls.push({
                object: object,
                method: method,
                arguments: args,
                line: line
            });
        }
        // Check if it's a simple function call
        else if (ts.isIdentifier(expression)) {
            this.result.functionCalls.push({
                function: expression.text,
                arguments: args,
                line: line
            });
        }
        // Handle more complex call expressions (e.g., immediately invoked functions, etc.)
        else {
            const callText = expression.getText();
            if (callText.length < 100) { // Only store if not too long
                this.result.functionCalls.push({
                    function: callText,
                    arguments: args,
                    line: line,
                    isComplex: true
                });
            }
        }
    }
    
    extractPropertyAccess(node) {
        // Skip if this is part of a call expression (already handled)
        if (node.parent && ts.isCallExpression(node.parent) && node.parent.expression === node) {
            return;
        }
        
        const object = node.expression.getText();
        const property = node.name.text;
        const line = this.getLineNumber(node);
        
        this.result.propertyAccesses.push({
            object: object,
            property: property,
            line: line
        });
    }
    
    extractNewExpression(node) {
        const className = node.expression.getText();
        const line = this.getLineNumber(node);
        
        // Extract constructor arguments
        const args = node.arguments?.map(arg => {
            if (ts.isStringLiteral(arg)) {
                return { type: 'string', value: arg.text };
            } else if (ts.isNumericLiteral(arg)) {
                return { type: 'number', value: arg.text };
            } else if (ts.isIdentifier(arg)) {
                return { type: 'identifier', value: arg.text };
            } else {
                return { type: 'expression', value: arg.getText().substring(0, 50) };
            }
        }) || [];
        
        this.result.constructorCalls.push({
            className: className,
            arguments: args,
            line: line
        });
    }
    
    enhanceVariableInfo(varInfo, initializer) {
        // Capture information about what the variable is initialized with
        if (!initializer) return;
        
        // Handle method call initializers (e.g., z.string(), someFunction())
        if (ts.isCallExpression(initializer)) {
            const expression = initializer.expression;
            
            // Handle property access calls (e.g., z.string())
            if (ts.isPropertyAccessExpression(expression)) {
                const object = expression.expression.getText();
                const method = expression.name.text;
                
                varInfo.initializer = {
                    type: 'methodCall',
                    object: object,
                    method: method,
                    arguments: initializer.arguments?.map(arg => arg.getText()) || []
                };
                
                // Infer type for common patterns
                if (object === 'z') {
                    // Zod schema methods
                    varInfo.inferredType = `Zod${method.charAt(0).toUpperCase() + method.slice(1)}Schema`;
                }
            }
            // Handle direct function calls
            else if (ts.isIdentifier(expression)) {
                varInfo.initializer = {
                    type: 'functionCall',
                    function: expression.text,
                    arguments: initializer.arguments?.map(arg => arg.getText()) || []
                };
            }
        }
        // Handle new expressions (e.g., new DataService())
        else if (ts.isNewExpression(initializer)) {
            const className = initializer.expression.getText();
            varInfo.initializer = {
                type: 'newExpression',
                className: className,
                arguments: initializer.arguments?.map(arg => arg.getText()) || []
            };
            varInfo.inferredType = className;
        }
        // Handle property access (e.g., someObject.someProperty)
        else if (ts.isPropertyAccessExpression(initializer)) {
            varInfo.initializer = {
                type: 'propertyAccess',
                object: initializer.expression.getText(),
                property: initializer.name.text
            };
        }
        // Handle object literals
        else if (ts.isObjectLiteralExpression(initializer)) {
            varInfo.initializer = {
                type: 'objectLiteral',
                propertyCount: initializer.properties.length
            };
            varInfo.inferredType = 'object';
        }
        // Handle array literals
        else if (ts.isArrayLiteralExpression(initializer)) {
            varInfo.initializer = {
                type: 'arrayLiteral',
                elementCount: initializer.elements.length
            };
            varInfo.inferredType = 'array';
        }
        // Handle string/number/boolean literals
        else if (ts.isStringLiteral(initializer)) {
            varInfo.initializer = {
                type: 'stringLiteral',
                value: initializer.text
            };
            varInfo.inferredType = 'string';
        }
        else if (ts.isNumericLiteral(initializer)) {
            varInfo.initializer = {
                type: 'numberLiteral',
                value: initializer.text
            };
            varInfo.inferredType = 'number';
        }
        else if (initializer.kind === ts.SyntaxKind.TrueKeyword || initializer.kind === ts.SyntaxKind.FalseKeyword) {
            varInfo.initializer = {
                type: 'booleanLiteral',
                value: initializer.kind === ts.SyntaxKind.TrueKeyword
            };
            varInfo.inferredType = 'boolean';
        }
        // Handle identifier references (e.g., const a = b)
        else if (ts.isIdentifier(initializer)) {
            varInfo.initializer = {
                type: 'identifier',
                name: initializer.text
            };
        }
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