"""
Validator configuration for TypeScript knowledge graph validator
"""

from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class ValidatorConfig:
    """Configuration for TypeScript validator"""
    # Neo4j connection
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "password"
    
    # Validation thresholds
    min_confidence: float = 0.7
    fuzzy_match_threshold: float = 0.8
    
    # Validation strictness
    strict_internal_imports: bool = False  # If True, missing internal imports are errors
    allow_missing_internal_modules: bool = True  # If True, missing internal modules are warnings
    trust_external_libraries: bool = True  # If True, assume all external libraries exist
    
    # Repository configuration
    repository_name: Optional[str] = None
    project_root: Optional[str] = None
    
    # Module resolution
    node_modules_paths: List[str] = None
    tsconfig_path: Optional[str] = None
    
    def __post_init__(self):
        if self.node_modules_paths is None:
            self.node_modules_paths = ["node_modules"]
    
    def is_external_library(self, module_name: str) -> bool:
        """Check if a module is an external library"""
        # First check for internal project patterns - these are NOT external
        internal_patterns = [
            '@/',  # Internal alias (e.g., @/components, @/utils)
            'src/',  # Source directory imports
            './',  # Relative imports
            '../',  # Relative imports
            '~/',  # Another common alias pattern
            '#/',  # Another possible alias pattern
        ]
        
        for pattern in internal_patterns:
            if module_name.startswith(pattern):
                return False
        
        # Check if it's an absolute path (internal)
        if module_name.startswith('/'):
            return False
        
        # Now check for known external libraries
        # Note: We removed '@' from this list since it needs special handling
        external_libraries = [
            # React ecosystem
            'react', 'react-dom', 'react-router', 'react-router-dom',
            'react-hook-form', 'react-query', '@tanstack/react-query',
            'react-i18next', 'i18next', 'react-helmet', 'react-helmet-async',
            'react-error-boundary', 'react-hot-toast', 'react-toastify',
            'react-select', 'react-datepicker', 'react-dnd', 'react-beautiful-dnd',
            'react-spring', '@react-spring', 'framer-motion', 'react-transition-group',
            'react-intersection-observer', 'react-use', 'ahooks', 'usehooks-ts',
            'react-aria', '@react-aria', 'react-stately', '@react-stately',
            'react-table', '@tanstack/react-table', 'react-window', 'react-virtualized',
            
            # State management
            'redux', '@reduxjs/toolkit', 'react-redux', 'mobx', 'mobx-react',
            'mobx-react-lite', 'recoil', 'zustand', 'jotai', 'valtio',
            'xstate', '@xstate/react', 'effector', 'effector-react',
            
            # Styling
            'styled-components', '@emotion/react', '@emotion/styled', 'emotion',
            '@mui/material', '@mui/icons-material', '@mui/system', 'material-ui',
            'antd', '@ant-design/icons', 'react-bootstrap', 'bootstrap',
            '@chakra-ui/react', '@mantine/core', '@headlessui/react',
            'tailwindcss', 'sass', 'less', 'postcss', '@stitches/react',
            
            # Forms and validation
            'formik', 'yup', 'zod', 'joi', '@hookform/resolvers',
            'react-final-form', 'final-form', 'vest', 'superstruct',
            
            # Data fetching
            'axios', 'ky', 'wretch', 'node-fetch', 'isomorphic-fetch',
            'swr', 'graphql', 'apollo', '@apollo/client', 'urql',
            'relay-runtime', 'react-relay',
            
            # Utilities
            'lodash', 'ramda', 'underscore', 'moment', 'date-fns', 'dayjs',
            'luxon', 'classnames', 'clsx', 'uuid', 'nanoid', 'shortid',
            'qs', 'query-string', 'path-to-regexp', 'immer', 'immutable',
            
            # Development tools
            'webpack', 'vite', 'rollup', 'parcel', 'esbuild', 'swc',
            'babel', '@babel', 'eslint', 'prettier', 'typescript',
            'jest', '@testing-library', 'vitest', 'mocha', 'chai', 'sinon',
            'enzyme', 'cypress', '@cypress', 'playwright', '@playwright',
            'puppeteer', 'selenium', 'storybook', '@storybook',
            
            # Framework specific
            'next', 'gatsby', 'remix', '@remix-run', 'vue', '@vue',
            'angular', '@angular', 'svelte', 'solid-js', 'preact',
            'express', 'koa', 'fastify', 'hapi', 'nestjs', '@nestjs',
            
            # Common Node.js built-ins
            'fs', 'path', 'os', 'crypto', 'http', 'https', 'url',
            'querystring', 'stream', 'util', 'events', 'buffer',
            'child_process', 'cluster', 'net', 'dns', 'readline',
            'zlib', 'assert', 'tty', 'vm', 'process', 'timers',
            'worker_threads', 'perf_hooks', 'async_hooks'
        ]
        
        # Check if module matches any known external library
        for lib in external_libraries:
            if module_name == lib or module_name.startswith(lib + '/'):
                return True
        
        # Handle scoped packages (e.g., @testing-library/react, @babel/core)
        # These are external UNLESS they match our internal patterns above
        if module_name.startswith('@'):
            # Split to check the scope
            parts = module_name.split('/')
            if len(parts) >= 2:
                # It's a scoped package like @scope/package
                # Since it didn't match internal patterns, it's external
                return True
        
        # If it's a simple name without path separators, it's likely external
        # (e.g., 'fs', 'path', 'crypto' - Node.js built-ins)
        if '/' not in module_name and '.' not in module_name:
            return True
            
        return False
    
    def is_internal_module(self, module_name: str) -> bool:
        """Check if a module is an internal project module"""
        # Relative imports are always internal
        if module_name.startswith('./') or module_name.startswith('../'):
            return True
        
        # Common internal alias patterns
        internal_aliases = ['@/', '~/', '#/', 'src/', 'app/', 'lib/', 'components/', 'utils/', 'services/', 'hooks/', 'pages/', 'views/']
        for alias in internal_aliases:
            if module_name.startswith(alias):
                return True
        
        # If it's an external library, it's not internal
        if self.is_external_library(module_name):
            return False
        
        # If it has no path separators and isn't external, it might be internal
        # This is less certain, so callers should handle accordingly
        return True
    
    def get_confidence(self, validation_type: str, found: bool, context: Optional[Dict] = None) -> float:
        """Get confidence score for a validation result"""
        base_confidence = 0.8 if found else 0.2
        
        # Adjust based on validation type
        type_adjustments = {
            'import': 0.1,
            'component': 0.15,
            'function': 0.1,
            'type': 0.1,
            'interface': 0.1,
            'hook': 0.15,
            'method': 0.1,
            'property': 0.05
        }
        
        adjustment = type_adjustments.get(validation_type, 0.0)
        
        if found:
            return min(1.0, base_confidence + adjustment)
        else:
            return max(0.0, base_confidence - adjustment)
    
    def is_html_element(self, tag_name: str) -> bool:
        """Check if a tag name is a standard HTML element"""
        # Common HTML elements
        html_elements = {
            'a', 'abbr', 'address', 'area', 'article', 'aside', 'audio',
            'b', 'base', 'bdi', 'bdo', 'blockquote', 'body', 'br', 'button',
            'canvas', 'caption', 'cite', 'code', 'col', 'colgroup',
            'data', 'datalist', 'dd', 'del', 'details', 'dfn', 'dialog', 'div', 'dl', 'dt',
            'em', 'embed',
            'fieldset', 'figcaption', 'figure', 'footer', 'form',
            'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'head', 'header', 'hgroup', 'hr', 'html',
            'i', 'iframe', 'img', 'input', 'ins',
            'kbd', 'label', 'legend', 'li', 'link',
            'main', 'map', 'mark', 'menu', 'meta', 'meter',
            'nav', 'noscript',
            'object', 'ol', 'optgroup', 'option', 'output',
            'p', 'param', 'picture', 'pre', 'progress',
            'q', 'rb', 'rp', 'rt', 'rtc', 'ruby',
            's', 'samp', 'script', 'section', 'select', 'slot', 'small', 'source', 'span',
            'strong', 'style', 'sub', 'summary', 'sup', 'svg',
            'table', 'tbody', 'td', 'template', 'textarea', 'tfoot', 'th', 'thead',
            'time', 'title', 'tr', 'track',
            'u', 'ul',
            'var', 'video',
            'wbr'
        }
        
        return tag_name.lower() in html_elements
    
    def is_react_type(self, type_name: str) -> bool:
        """Check if a type is a common React type"""
        react_types = {
            'React.FC', 'React.FunctionComponent', 'React.Component',
            'React.ReactNode', 'React.ReactElement', 'React.CSSProperties',
            'React.MouseEvent', 'React.ChangeEvent', 'React.FormEvent',
            'React.KeyboardEvent', 'React.SyntheticEvent',
            'JSX.Element', 'JSX.IntrinsicElements',
            'FC', 'FunctionComponent', 'ReactNode', 'ReactElement',
            'MouseEvent', 'ChangeEvent', 'FormEvent', 'KeyboardEvent'
        }
        return type_name in react_types
    
    def is_react_hook(self, hook_name: str) -> bool:
        """Check if a function is a React hook"""
        # Built-in React hooks
        react_hooks = {
            'useState', 'useEffect', 'useContext', 'useReducer',
            'useCallback', 'useMemo', 'useRef', 'useImperativeHandle',
            'useLayoutEffect', 'useDebugValue', 'useId', 'useTransition',
            'useDeferredValue', 'useSyncExternalStore', 'useInsertionEffect'
        }
        
        # Hook naming convention - starts with 'use' followed by capital letter
        if hook_name.startswith('use') and len(hook_name) > 3 and hook_name[3].isupper():
            return True
        
        return hook_name in react_hooks
    
    def get_service_method_patterns(self) -> Dict[str, List[str]]:
        """Get common service method patterns to trust"""
        return {
            # Data services
            'dataService': [
                'get', 'getAll', 'getById', 'getByIds', 'getOne', 'getMany',
                'fetch', 'fetchAll', 'fetchById', 'fetchOne', 'fetchMany',
                'fetchBusinessById', 'saveApplication', 'getFromCache', 'setCache',
                'find', 'findAll', 'findById', 'findOne', 'findMany', 'findByQuery',
                'search', 'query', 'filter', 'sort', 'paginate',
                'save', 'saveAll', 'create', 'createMany', 'insert', 'insertMany',
                'update', 'updateById', 'updateMany', 'patch', 'patchById',
                'delete', 'deleteById', 'deleteMany', 'remove', 'removeById',
                'upsert', 'replace', 'replaceById',
                'count', 'exists', 'existsById',
                'cache', 'cacheAll', 'clearCache', 'invalidateCache',
                'subscribe', 'unsubscribe', 'watch', 'observe',
                'validate', 'validateAll', 'sanitize',
                'getFallbackData', 'getDefault', 'getDefaults',
                'batch', 'batchGet', 'batchCreate', 'batchUpdate', 'batchDelete',
                'aggregate', 'groupBy', 'sum', 'average', 'min', 'max',
                'export', 'import', 'sync', 'replicate',
                'lock', 'unlock', 'transaction', 'commit', 'rollback'
            ],
            
            # Email services
            'emailService': [
                'send', 'sendEmail', 'sendMail', 'sendAsync', 'sendBatch',
                'queue', 'queueEmail', 'queueMail', 'schedule', 'scheduleEmail',
                'sendWithTemplate', 'sendTemplate', 'renderTemplate',
                'validate', 'validateEmail', 'validateAddress', 'verify',
                'test', 'testConnection', 'ping',
                'addRecipient', 'addRecipients', 'setRecipients',
                'addAttachment', 'addAttachments', 'attach',
                'setSubject', 'setBody', 'setContent', 'setHtml', 'setText',
                'setFrom', 'setSender', 'setReplyTo',
                'addHeader', 'setHeaders', 'setPriority',
                'track', 'trackEmail', 'getStatus', 'getDeliveryStatus',
                'resend', 'retry', 'cancel', 'cancelScheduled',
                'getTemplates', 'getTemplate', 'saveTemplate', 'deleteTemplate',
                'subscribe', 'unsubscribe', 'getSubscribers',
                'blacklist', 'whitelist', 'isBlacklisted'
            ],
            
            # Validation services
            'validationService': [
                'validate', 'validateAll', 'validateField', 'validateFields',
                'validateEmail', 'validatePhone', 'validateUrl', 'validateDate',
                'validatePassword', 'validateUsername', 'validateAddress',
                'validateCreditCard', 'validateSSN', 'validateTaxId',
                'validateBusinessApplication', 'validateApplication', 'validateForm',
                'validateData', 'validateInput', 'validateRequest', 'validateResponse',
                'validateUpdate', 'validateCreate', 'validateDelete',
                'validateEmailData', 'check', 'checkAll', 'checkField', 'checkFormat',
                'verify', 'verifyAll', 'verifyEmail', 'verifyPhone',
                'sanitize', 'sanitizeAll', 'sanitizeInput', 'clean',
                'normalize', 'normalizeAll', 'format', 'formatAll',
                'isValid', 'isValidEmail', 'isValidPhone', 'isValidUrl',
                'getErrors', 'getValidationErrors', 'hasErrors', 'clearErrors',
                'addRule', 'addRules', 'setRules', 'getRules',
                'addValidator', 'removeValidator', 'getValidators',
                'test', 'testPattern', 'matches', 'matchesPattern'
            ],
            
            # Analytics services
            'analyticsService': [
                'track', 'trackEvent', 'trackPageView', 'trackAction',
                'trackError', 'trackException', 'trackCrash',
                'trackUser', 'trackSession', 'trackConversion',
                'log', 'logEvent', 'logError', 'logMetric',
                'measure', 'measurePerformance', 'measureTime',
                'startTimer', 'stopTimer', 'recordTime',
                'report', 'reportMetric', 'reportError', 'reportUsage',
                'send', 'sendEvent', 'sendMetrics', 'flush',
                'identify', 'identifyUser', 'setUser', 'setUserId',
                'setProperty', 'setProperties', 'setUserProperty',
                'increment', 'decrement', 'addMetric',
                'startProcess', 'endProcess', 'completeProcess',
                'startSession', 'endSession', 'pauseSession',
                'enable', 'disable', 'isEnabled', 'reset',
                'getMetrics', 'getEvents', 'getReports',
                'query', 'queryEvents', 'queryMetrics',
                'export', 'exportData', 'generateReport'
            ],
            
            # Notification services
            'notificationService': [
                'notify', 'notifyAll', 'notifyUser', 'notifyUsers',
                'notifyAdmins', 'notifyModerators', 'notifyGroup',
                'send', 'sendNotification', 'sendAlert', 'sendMessage',
                'push', 'pushNotification', 'pushAlert',
                'queue', 'queueNotification', 'schedule', 'scheduleNotification',
                'broadcast', 'broadcastMessage', 'broadcastAlert',
                'show', 'showNotification', 'display', 'displayAlert',
                'toast', 'showToast', 'alert', 'showAlert',
                'success', 'error', 'warning', 'info', 'log',
                'dismiss', 'dismissAll', 'clear', 'clearAll',
                'markAsRead', 'markAsUnread', 'markAllAsRead',
                'subscribe', 'unsubscribe', 'getSubscribers',
                'mute', 'unmute', 'isMuted', 'setPreferences',
                'getNotifications', 'getUnread', 'getHistory',
                'delete', 'deleteNotification', 'archive',
                'setPriority', 'setChannel', 'setType',
                'addAction', 'addActions', 'handleAction'
            ],
            
            # Auth services
            'authService': [
                'login', 'logout', 'authenticate', 'authorize',
                'register', 'signup', 'createAccount', 'createUser',
                'verify', 'verifyEmail', 'verifyPhone', 'confirmEmail',
                'getCurrentUser', 'getUser', 'getUserById', 'getProfile',
                'updateProfile', 'updateUser', 'updatePassword',
                'resetPassword', 'forgotPassword', 'changePassword',
                'refresh', 'refreshToken', 'renewToken', 'getToken',
                'validate', 'validateToken', 'validateSession',
                'isAuthenticated', 'isAuthorized', 'hasPermission',
                'checkAuth', 'checkPermission', 'checkRole',
                'grant', 'grantAccess', 'grantPermission', 'grantRole',
                'revoke', 'revokeAccess', 'revokePermission', 'revokeRole',
                'enable2FA', 'disable2FA', 'verify2FA', 'generate2FA',
                'lockAccount', 'unlockAccount', 'suspendAccount',
                'deleteAccount', 'deactivateAccount', 'reactivateAccount',
                'getPermissions', 'getRoles', 'getGroups',
                'impersonate', 'stopImpersonation'
            ],
            
            # Cache services
            'cacheService': [
                'get', 'getMany', 'getAll', 'getValue', 'fetch',
                'set', 'setMany', 'put', 'store', 'save',
                'has', 'exists', 'contains', 'includes',
                'delete', 'deleteMany', 'remove', 'evict',
                'clear', 'clearAll', 'flush', 'reset', 'purge',
                'invalidate', 'invalidateAll', 'invalidatePattern',
                'refresh', 'refreshAll', 'reload', 'update',
                'expire', 'setExpiry', 'setTTL', 'getTTL',
                'increment', 'decrement', 'add', 'subtract',
                'remember', 'rememberForever', 'getOrSet',
                'pull', 'pullMany', 'pop', 'push',
                'tags', 'tag', 'getByTag', 'flushByTag',
                'lock', 'unlock', 'isLocked', 'waitForLock',
                'getStats', 'getSize', 'getKeys', 'getMetadata',
                'warmUp', 'preload', 'prefetch', 'prewarm'
            ],
            
            # Storage services
            'storageService': [
                'upload', 'uploadFile', 'uploadFiles', 'uploadMany',
                'download', 'downloadFile', 'downloadFiles', 'downloadMany',
                'get', 'getFile', 'getFiles', 'retrieve', 'fetch',
                'save', 'saveFile', 'store', 'storeFile', 'put',
                'delete', 'deleteFile', 'deleteFiles', 'remove', 'removeFile',
                'move', 'moveFile', 'rename', 'renameFile', 'relocate',
                'copy', 'copyFile', 'duplicate', 'clone',
                'exists', 'fileExists', 'has', 'contains',
                'list', 'listFiles', 'getDirectory', 'readDir',
                'createFolder', 'createDirectory', 'mkdir',
                'deleteFolder', 'deleteDirectory', 'rmdir',
                'getUrl', 'getPublicUrl', 'getSignedUrl', 'generateUrl',
                'getMetadata', 'setMetadata', 'updateMetadata',
                'getSize', 'getFileSize', 'calculateSize',
                'compress', 'decompress', 'zip', 'unzip',
                'encrypt', 'decrypt', 'sign', 'verify',
                'stream', 'streamFile', 'pipe', 'chunk'
            ],
            
            # Payment services
            'paymentService': [
                'charge', 'createCharge', 'processPayment', 'pay',
                'authorize', 'capture', 'void', 'cancel',
                'refund', 'createRefund', 'processRefund', 'reverseCharge',
                'createCustomer', 'updateCustomer', 'deleteCustomer', 'getCustomer',
                'addCard', 'updateCard', 'deleteCard', 'setDefaultCard',
                'createSubscription', 'updateSubscription', 'cancelSubscription',
                'createInvoice', 'sendInvoice', 'payInvoice', 'getInvoice',
                'createPaymentMethod', 'attachPaymentMethod', 'detachPaymentMethod',
                'confirmPayment', 'validatePayment', 'verifyPayment',
                'getBalance', 'getTransactions', 'getCharges', 'getPayments',
                'calculateFees', 'calculateTax', 'calculateTotal',
                'webhook', 'handleWebhook', 'verifyWebhook',
                'test', 'testCard', 'validateCard', 'checkCard',
                'dispute', 'respondToDispute', 'getDisputes',
                'payout', 'createPayout', 'transfer', 'createTransfer'
            ],
            
            # Queue services  
            'queueService': [
                'add', 'addJob', 'enqueue', 'push', 'publish',
                'addBulk', 'enqueueBulk', 'pushMany', 'publishMany',
                'process', 'processJob', 'consume', 'handle',
                'pause', 'resume', 'stop', 'start', 'restart',
                'remove', 'removeJob', 'delete', 'cancel',
                'retry', 'retryJob', 'requeue', 'reschedule',
                'delay', 'schedule', 'scheduleJob', 'later',
                'getJob', 'getJobs', 'getStatus', 'getProgress',
                'count', 'getCount', 'size', 'length',
                'clear', 'empty', 'drain', 'flush', 'purge',
                'peek', 'peekNext', 'getNext', 'getWaiting',
                'complete', 'completeJob', 'finish', 'done',
                'fail', 'failJob', 'error', 'reject',
                'on', 'addEventListener', 'subscribe', 'listen',
                'off', 'removeEventListener', 'unsubscribe',
                'getWorkers', 'getActiveJobs', 'getCompletedJobs',
                'getFailedJobs', 'getDelayedJobs', 'getWaitingJobs'
            ]
        }
    
    def is_trusted_service_method(self, object_name: str, method_name: str) -> bool:
        """Check if a method is a trusted service method pattern"""
        service_patterns = self.get_service_method_patterns()
        
        # Check exact service name match
        if object_name in service_patterns:
            return method_name in service_patterns[object_name]
        
        # Check if object name ends with common service suffixes
        service_suffixes = ['Service', 'Manager', 'Provider', 'Repository', 'Store', 'Client', 'Api', 'Helper', 'Util', 'Utils']
        for suffix in service_suffixes:
            if object_name.endswith(suffix):
                # Try to find a matching base pattern
                base_name = object_name[:-len(suffix)].lower() + 'Service'
                if base_name in service_patterns:
                    return method_name in service_patterns[base_name]
                
                # Check if method matches common service patterns
                for pattern_methods in service_patterns.values():
                    if method_name in pattern_methods:
                        return True
        
        # Check if method matches common service method prefixes
        common_prefixes = [
            'get', 'set', 'fetch', 'save', 'create', 'update', 'delete', 'remove',
            'find', 'search', 'query', 'validate', 'verify', 'check', 'test',
            'send', 'queue', 'process', 'handle', 'execute', 'run', 'start', 'stop',
            'subscribe', 'unsubscribe', 'on', 'off', 'emit', 'dispatch',
            'cache', 'clear', 'flush', 'invalidate', 'refresh', 'reload',
            'track', 'log', 'report', 'measure', 'record', 'capture',
            'authenticate', 'authorize', 'login', 'logout', 'register',
            'upload', 'download', 'store', 'retrieve', 'archive',
            'notify', 'alert', 'broadcast', 'publish', 'announce'
        ]
        
        for prefix in common_prefixes:
            if method_name.startswith(prefix) and len(method_name) > len(prefix):
                # Check if next character is uppercase (camelCase)
                if method_name[len(prefix)].isupper():
                    return True
        
        return False
    
    def is_common_ui_component(self, component_name: str) -> bool:
        """Check if a component is a common UI component pattern"""
        # Common UI component names found in most UI libraries
        common_ui_components = {
            # Layout components
            'Container', 'Box', 'Grid', 'Row', 'Column', 'Layout', 'Stack',
            'Flex', 'FlexBox', 'Spacer', 'Divider', 'Section', 'Panel',
            
            # Basic components
            'Button', 'IconButton', 'Link', 'Text', 'Label', 'Icon',
            'Image', 'Avatar', 'Badge', 'Tag', 'Chip', 'Card', 'CardHeader',
            'CardBody', 'CardFooter', 'CardContent', 'CardTitle',
            
            # Form components
            'Input', 'TextInput', 'TextField', 'TextArea', 'Textarea',
            'Select', 'SelectOption', 'Option', 'Checkbox', 'CheckBox',
            'Radio', 'RadioButton', 'RadioGroup', 'Switch', 'Toggle',
            'Slider', 'RangeSlider', 'DatePicker', 'TimePicker',
            'ColorPicker', 'FileInput', 'FileUpload', 'Form', 'FormField',
            'FormGroup', 'FormControl', 'FormLabel', 'FormHelperText',
            'FormErrorMessage', 'SearchInput', 'SearchBox',
            
            # Overlay components
            'Modal', 'Dialog', 'Popover', 'Popup', 'Tooltip', 'Toast',
            'Alert', 'AlertDialog', 'Drawer', 'Sheet', 'Overlay',
            'Backdrop', 'Portal', 'DropdownMenu', 'Dropdown', 'Menu',
            'MenuItem', 'MenuGroup', 'MenuDivider', 'ContextMenu',
            
            # Navigation components
            'Nav', 'Navbar', 'Navigation', 'Header', 'Footer', 'Sidebar',
            'Breadcrumb', 'BreadcrumbItem', 'Tabs', 'Tab', 'TabList',
            'TabPanel', 'TabPanels', 'Steps', 'Stepper', 'Step',
            'Pagination', 'PageItem', 'Anchor', 'NavLink',
            
            # Data display components
            'Table', 'TableHead', 'TableBody', 'TableRow', 'TableCell',
            'TableHeader', 'TableFooter', 'DataTable', 'List', 'ListItem',
            'DescriptionList', 'Accordion', 'AccordionItem', 'Collapse',
            'Collapsible', 'Tree', 'TreeNode', 'TreeItem',
            
            # Feedback components
            'Progress', 'ProgressBar', 'Spinner', 'Loader', 'Loading',
            'Skeleton', 'SkeletonText', 'SkeletonCircle', 'Placeholder',
            'Empty', 'EmptyState', 'ErrorBoundary', 'Error',
            
            # Media components
            'Video', 'VideoPlayer', 'Audio', 'AudioPlayer', 'Carousel',
            'Gallery', 'Lightbox', 'ImageGallery',
            
            # Typography components
            'Heading', 'Title', 'Subtitle', 'Paragraph', 'Caption',
            'Quote', 'BlockQuote', 'Code', 'Pre', 'Kbd', 'Mark',
            
            # Utility components
            'Portal', 'Transition', 'Fade', 'Slide', 'Zoom', 'Collapse',
            'AnimationWrapper', 'LazyLoad', 'InfiniteScroll',
            'VirtualList', 'Observer', 'IntersectionObserver'
        }
        
        return component_name in common_ui_components
    
    def is_ui_library_import(self, module_path: str) -> bool:
        """Check if an import is from a UI library path pattern"""
        ui_library_patterns = [
            '@/components/ui',  # Common UI component alias (with or without trailing slash)
            '@/ui',  # Shorter UI alias
            '@/lib/ui',  # UI library location
            'components/ui',  # Direct UI path
            'ui/',  # Simple UI path (keep trailing slash for this one to avoid false positives)
            '@ui',  # UI scope
            '~/components/ui',  # Home alias UI path
            './components/ui',  # Relative UI path
            '../components/ui',  # Parent relative UI path
            '@/shared/ui',  # Shared UI components
            'shared/ui',  # Shared without alias
        ]
        
        # Check both with and without trailing slash
        return any(
            module_path == pattern or 
            module_path.startswith(pattern + '/') or
            module_path.startswith(pattern + '\\')  # Windows path separator
            for pattern in ui_library_patterns
        )
    
    def get_external_library_exports(self, module_name: str) -> Optional[List[str]]:
        """Get known exports from popular external libraries"""
        # Common exports from popular libraries
        known_exports = {
            'react-router-dom': [
                'BrowserRouter', 'HashRouter', 'MemoryRouter', 'Router',
                'Link', 'NavLink', 'Navigate', 'Outlet',
                'Route', 'Routes',
                'useNavigate', 'useLocation', 'useParams', 'useSearchParams',
                'useRoutes', 'useHref', 'useInRouterContext', 'useNavigationType',
                'useOutlet', 'useOutletContext', 'useResolvedPath', 'useMatch',
                'useMatches', 'useLoaderData', 'useActionData', 'useAsyncValue',
                'useAsyncError', 'useRouteError', 'useRouteLoaderData',
                'generatePath', 'matchPath', 'matchRoutes', 'resolvePath',
                'createBrowserRouter', 'createHashRouter', 'createMemoryRouter',
                'RouterProvider', 'createRoutesFromElements', 'renderMatches'
            ],
            'react-i18next': [
                'useTranslation', 'withTranslation', 'Trans', 'Translation',
                'I18nextProvider', 'initReactI18next', 'withSSR', 'useSSR',
                'I18nextContext', 'i18n', 'getI18n', 'setI18n', 'composeInitialProps',
                'getInitialProps'
            ],
            'framer-motion': [
                'motion', 'AnimatePresence', 'MotionConfig', 'LazyMotion',
                'LayoutGroup', 'AnimateSharedLayout', 'MotionValue',
                'useMotionValue', 'useTransform', 'useSpring', 'useVelocity',
                'useScroll', 'useTime', 'useAnimation', 'useAnimationControls',
                'useCycle', 'usePresence', 'useIsPresent', 'useDragControls',
                'useMotionTemplate', 'useMotionValueEvent', 'useViewportScroll',
                'useReducedMotion', 'useInView', 'animate', 'animateValue',
                'transform', 'clamp', 'delay', 'stagger', 'spring', 'inertia'
            ],
            'react-hook-form': [
                'useForm', 'useController', 'useFormContext', 'useWatch',
                'useFormState', 'useFieldArray', 'Controller', 'FormProvider',
                'get', 'set', 'useSubscribe'
            ],
            'zod': [
                'z', 'ZodType', 'ZodSchema', 'ZodError', 'ZodIssue',
                'string', 'number', 'boolean', 'date', 'object', 'array',
                'union', 'discriminatedUnion', 'intersection', 'tuple',
                'record', 'map', 'set', 'function', 'lazy', 'literal',
                'enum', 'nativeEnum', 'promise', 'instanceof', 'preprocess',
                'custom', 'refine', 'superRefine', 'transform', 'default',
                'optional', 'nullable', 'nullish', 'branded', 'BRAND',
                'any', 'unknown', 'never', 'void', 'undefined', 'null'
            ],
            '@hookform/resolvers': [
                'zodResolver', 'yupResolver', 'superstructResolver',
                'joiResolver', 'vestResolver', 'classValidatorResolver',
                'ioTsResolver', 'nevalResolver', 'computedTypesResolver',
                'typeboxResolver', 'ajvResolver'
            ]
        }
        
        return known_exports.get(module_name)
    
    def is_trusted_external_pattern(self, module_name: str) -> bool:
        """Check if module matches a trusted external pattern"""
        trusted_patterns = [
            r'^react-',  # Any react-* package
            r'^@react-',  # Any @react-* scoped package
            r'^@mui/',  # Material-UI packages
            r'^@emotion/',  # Emotion packages
            r'^@tanstack/',  # TanStack packages
            r'^@testing-library/',  # Testing Library packages
            r'^@babel/',  # Babel packages
            r'^@types/',  # TypeScript type definitions
            r'^@storybook/',  # Storybook packages
            r'^@hookform/',  # React Hook Form packages
            r'^node:',  # Node.js protocol imports
        ]
        
        import re
        for pattern in trusted_patterns:
            if re.match(pattern, module_name):
                return True
        return False
    
    def merge(self, other: 'ValidatorConfig') -> 'ValidatorConfig':
        """Merge this config with another config, with other taking precedence"""
        import copy
        result = copy.deepcopy(self)
        
        # Merge attributes from other config if they're not None
        if other.neo4j_uri is not None:
            result.neo4j_uri = other.neo4j_uri
        if other.neo4j_user is not None:
            result.neo4j_user = other.neo4j_user
        if other.neo4j_password is not None:
            result.neo4j_password = other.neo4j_password
        if other.min_confidence is not None:
            result.min_confidence = other.min_confidence
        if other.fuzzy_match_threshold is not None:
            result.fuzzy_match_threshold = other.fuzzy_match_threshold
        if other.repository_name is not None:
            result.repository_name = other.repository_name
        if other.project_root is not None:
            result.project_root = other.project_root
        if other.node_modules_paths is not None:
            result.node_modules_paths = other.node_modules_paths
        if other.tsconfig_path is not None:
            result.tsconfig_path = other.tsconfig_path
            
        return result


def get_project_config(project_root: Optional[str] = None) -> ValidatorConfig:
    """Get configuration for a specific project"""
    import os
    
    config = ValidatorConfig()
    
    # Override from environment variables
    config.neo4j_uri = os.getenv("NEO4J_URI", config.neo4j_uri)
    config.neo4j_user = os.getenv("NEO4J_USER", config.neo4j_user)
    config.neo4j_password = os.getenv("NEO4J_PASSWORD", config.neo4j_password)
    
    if project_root:
        config.project_root = project_root
        
    return config