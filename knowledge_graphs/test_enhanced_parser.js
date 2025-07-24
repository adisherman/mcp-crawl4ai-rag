const { parentPort } = require('worker_threads');

// Load the enhanced parser
const parserPath = './knowledge_graphs/parser_worker_enhanced.js';
delete require.cache[require.resolve(parserPath)];
const { EnhancedASTExtractor } = require(parserPath);

const ts = require('typescript');

const code = `
function test() {
  const obj = new MyClass();
  obj.method();
  someFunction();
}
`;

const sourceFile = ts.createSourceFile(
    'test.ts',
    code,
    ts.ScriptTarget.Latest,
    true,
    ts.ScriptKind.TS
);

const extractor = new EnhancedASTExtractor(sourceFile);
const result = extractor.extract();

console.log('functionCalls:', result.functionCalls.length);
console.log('methodCalls:', result.methodCalls.length);
console.log('constructorCalls:', result.constructorCalls.length);

console.log('\nFull result:', JSON.stringify(result, null, 2));
