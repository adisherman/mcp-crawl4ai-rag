#!/usr/bin/env node
/**
 * TypeScript Parser Service
 * 
 * A REST API service that uses the TypeScript Compiler API to parse
 * TypeScript and JavaScript files, extracting complete AST information
 * for storage in Neo4j knowledge graphs.
 */

const express = require('express');
const ts = require('typescript');
const { Worker } = require('worker_threads');
const path = require('path');
const fs = require('fs').promises;
const os = require('os');

const app = express();
app.use(express.json({ limit: '50mb' }));

// Configuration
const PORT = process.env.PARSER_PORT || 3456;
const NUM_WORKERS = process.env.PARSER_WORKERS || os.cpus().length;

// Worker pool for parallel parsing
class WorkerPool {
    constructor(workerPath, poolSize) {
        this.workers = [];
        this.freeWorkers = [];
        this.queue = [];
        
        for (let i = 0; i < poolSize; i++) {
            this.addWorker(workerPath);
        }
    }
    
    addWorker(workerPath) {
        const worker = new Worker(workerPath);
        worker.on('message', (result) => {
            worker.currentResolve(result);
            worker.currentResolve = null;
            this.freeWorkers.push(worker);
            this.processQueue();
        });
        worker.on('error', (error) => {
            if (worker.currentReject) {
                worker.currentReject(error);
            }
        });
        this.workers.push(worker);
        this.freeWorkers.push(worker);
    }
    
    async parse(data) {
        return new Promise((resolve, reject) => {
            const task = { data, resolve, reject };
            
            if (this.freeWorkers.length > 0) {
                this.executeTask(task);
            } else {
                this.queue.push(task);
            }
        });
    }
    
    executeTask(task) {
        const worker = this.freeWorkers.pop();
        worker.currentResolve = task.resolve;
        worker.currentReject = task.reject;
        worker.postMessage(task.data);
    }
    
    processQueue() {
        if (this.queue.length > 0 && this.freeWorkers.length > 0) {
            const task = this.queue.shift();
            this.executeTask(task);
        }
    }
    
    async terminate() {
        await Promise.all(this.workers.map(w => w.terminate()));
    }
}

// Initialize worker pool - use fixed parser that avoids module resolution
const workerPool = new WorkerPool(
    path.join(__dirname, 'parser_worker_enhanced.js'),
    NUM_WORKERS
);

// Compiler options for parsing - optimized for AST extraction without type checking
const defaultCompilerOptions = {
    allowJs: true,
    checkJs: false,
    jsx: ts.JsxEmit.React,
    target: ts.ScriptTarget.ES2022,
    module: ts.ModuleKind.ESNext,
    moduleResolution: ts.ModuleResolutionKind.Bundler,
    esModuleInterop: true,
    allowSyntheticDefaultImports: true,
    strict: false,
    skipLibCheck: true,
    skipDefaultLibCheck: true,
    resolveJsonModule: true,
    noResolve: true,  // Don't try to resolve external modules
    isolatedModules: true,  // Treat each file independently
    allowImportingTsExtensions: true,
    noLib: false,  // Still use lib for basic types
    suppressOutputPathCheck: true
};

/**
 * Parse a single file endpoint
 */
app.post('/parse-file', async (req, res) => {
    try {
        const { content, filename, compilerOptions = {} } = req.body;
        
        if (!content || !filename) {
            return res.status(400).json({ 
                error: 'Missing required fields: content and filename' 
            });
        }
        
        // Merge compiler options
        const options = { ...defaultCompilerOptions, ...compilerOptions };
        
        // Use worker pool for parsing
        const result = await workerPool.parse({ 
            content, 
            filename, 
            options 
        });
        
        res.json(result);
    } catch (error) {
        console.error('Parse error:', error);
        res.status(500).json({ 
            error: error.message,
            stack: process.env.NODE_ENV === 'development' ? error.stack : undefined
        });
    }
});

/**
 * Parse multiple files endpoint (batch processing)
 */
app.post('/parse-batch', async (req, res) => {
    try {
        const { files, compilerOptions = {} } = req.body;
        
        if (!Array.isArray(files) || files.length === 0) {
            return res.status(400).json({ 
                error: 'Files must be a non-empty array' 
            });
        }
        
        // Merge compiler options
        const options = { ...defaultCompilerOptions, ...compilerOptions };
        
        // Parse files in parallel using worker pool
        const parsePromises = files.map(file => 
            workerPool.parse({
                content: file.content,
                filename: file.filename,
                options
            }).then(result => ({
                filename: file.filename,
                result
            })).catch(error => ({
                filename: file.filename,
                error: error.message
            }))
        );
        
        const results = await Promise.all(parsePromises);
        
        res.json({ results });
    } catch (error) {
        console.error('Batch parse error:', error);
        res.status(500).json({ 
            error: error.message,
            stack: process.env.NODE_ENV === 'development' ? error.stack : undefined
        });
    }
});

/**
 * Health check endpoint
 */
app.get('/health', (req, res) => {
    res.json({ 
        status: 'healthy',
        workers: NUM_WORKERS,
        typescript_version: ts.version,
        uptime: process.uptime()
    });
});

/**
 * Get TypeScript version and capabilities
 */
app.get('/info', (req, res) => {
    res.json({
        typescript_version: ts.version,
        supported_extensions: ['.ts', '.tsx', '.js', '.jsx', '.mts', '.cts', '.mjs', '.cjs'],
        jsx_support: true,
        decorators_support: true,
        worker_threads: NUM_WORKERS,
        features: {
            react_components: true,
            vue_components: false, // Could be added
            type_extraction: true,
            jsdoc_parsing: true,
            flow_type_support: false
        }
    });
});

// Error handling middleware
app.use((err, req, res, next) => {
    console.error('Unhandled error:', err);
    res.status(500).json({ 
        error: 'Internal server error',
        message: err.message 
    });
});

// Graceful shutdown
process.on('SIGTERM', async () => {
    console.log('SIGTERM received, shutting down gracefully...');
    await workerPool.terminate();
    process.exit(0);
});

process.on('SIGINT', async () => {
    console.log('SIGINT received, shutting down gracefully...');
    await workerPool.terminate();
    process.exit(0);
});

// Start server
app.listen(PORT, () => {
    console.log(`TypeScript Parser Service running on port ${PORT}`);
    console.log(`Worker threads: ${NUM_WORKERS}`);
    console.log(`TypeScript version: ${ts.version}`);
});

module.exports = app;