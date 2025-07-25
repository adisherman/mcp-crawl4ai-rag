// Test file to verify built-in constructor and function validation

// Built-in constructors
const date1 = new Date();
const date2 = new Date('2024-01-01');
const date3 = new Date(2024, 0, 1);

const error1 = new Error('Something went wrong');
const typeError = new TypeError('Invalid type');
const rangeError = new RangeError('Out of range');
const syntaxError = new SyntaxError('Invalid syntax');

const promise1 = new Promise((resolve, reject) => {
  resolve('done');
});

const map1 = new Map();
const set1 = new Set();
const weakMap = new WeakMap();
const weakSet = new WeakSet();

const array1 = new Array(10);
const obj1 = new Object();
const func1 = new Function('a', 'b', 'return a + b');
const regex1 = new RegExp('\\d+', 'g');

const url1 = new URL('https://example.com');
const urlParams = new URLSearchParams('key=value');

// Typed arrays
const int8 = new Int8Array(10);
const uint8 = new Uint8Array(10);
const float32 = new Float32Array(10);

// Built-in global functions
const num1 = parseInt('123');
const num2 = parseFloat('123.45');
const isNotANumber = isNaN(NaN);
const isFiniteNum = isFinite(100);

const encoded1 = encodeURI('https://example.com/path with spaces');
const decoded1 = decodeURI(encoded1);
const encoded2 = encodeURIComponent('key=value&other=data');
const decoded2 = decodeURIComponent(encoded2);

// Browser-specific globals (should also be valid)
const base64 = btoa('hello');
const decoded = atob(base64);

// Static methods on built-in objects (already handled)
const arr = Array.from([1, 2, 3]);
const isArr = Array.isArray(arr);
const obj = Object.create(null);
const frozen = Object.freeze({});
const resolved = Promise.resolve(42);
const rejected = Promise.reject(new Error('failed'));
const random = Math.random();
const max = Math.max(1, 2, 3);

// Method calls on instances (already handled)
const dateStr = date1.toISOString();
const errorMsg = error1.message;
const mapSize = map1.size;
const arrLength = array1.length;

export { date1, error1, promise1, map1, num1 };