// ESLint 配置 - Vue 3.5 + TypeScript
// 生成时间: 2025-09-07 22:15

import js from '@eslint/js';
import vue from 'eslint-plugin-vue';
import typescript from '@typescript-eslint/eslint-plugin';
import typescriptParser from '@typescript-eslint/parser';
import vueParser from 'vue-eslint-parser';

export default [
  // JavaScript 基础配置
  js.configs.recommended,
  
  // Vue 文件配置
  {
    files: ['**/*.vue'],
    languageOptions: {
      parser: vueParser,
      parserOptions: {
        parser: typescriptParser,
        ecmaVersion: 'latest',
        sourceType: 'module',
        extraFileExtensions: ['.vue']
      },
      globals: {
        defineProps: 'readonly',
        defineEmits: 'readonly',
        defineExpose: 'readonly',
        withDefaults: 'readonly',
        defineSlots: 'readonly',
        defineModel: 'readonly'
      }
    },
    plugins: {
      vue: vue,
      '@typescript-eslint': typescript
    },
    rules: {
      // Vue 3.5 特定规则
      ...vue.configs['vue3-recommended'].rules,
      
      // TypeScript 规则
      '@typescript-eslint/no-unused-vars': 'error',
      '@typescript-eslint/no-explicit-any': 'error',
      '@typescript-eslint/explicit-function-return-type': 'warn',
      '@typescript-eslint/no-non-null-assertion': 'warn',
      '@typescript-eslint/prefer-const': 'error',
      '@typescript-eslint/no-inferrable-types': 'error',
      
      // Vue 自定义规则
      'vue/multi-word-component-names': 'off',
      'vue/no-v-html': 'off',
      'vue/require-default-prop': 'error',
      'vue/require-prop-types': 'error',
      'vue/component-definition-name-casing': ['error', 'PascalCase'],
      'vue/component-name-in-template-casing': ['error', 'kebab-case'],
      'vue/prop-name-casing': ['error', 'camelCase'],
      'vue/attribute-hyphenation': ['error', 'always'],
      'vue/v-on-event-hyphenation': ['error', 'always'],
      
      // Vue 3.5 组合式 API 规则
      'vue/no-setup-props-destructure': 'error',
      'vue/no-duplicate-attr-inheritance': 'error',
      'vue/no-useless-v-bind': 'error',
      'vue/no-unused-refs': 'error',
      'vue/prefer-import-from-vue': 'error',
      
      // 代码质量规则
      'no-console': process.env.NODE_ENV === 'production' ? 'error' : 'warn',
      'no-debugger': process.env.NODE_ENV === 'production' ? 'error' : 'warn',
      'no-unused-vars': 'off', // 使用 TypeScript 版本
      'no-undef': 'off', // TypeScript 处理
      'prefer-const': 'error',
      'no-var': 'error',
    }
  },
  
  // TypeScript 文件配置
  {
    files: ['**/*.ts', '**/*.tsx'],
    languageOptions: {
      parser: typescriptParser,
      parserOptions: {
        ecmaVersion: 'latest',
        sourceType: 'module',
        project: './tsconfig.json'
      }
    },
    plugins: {
      '@typescript-eslint': typescript
    },
    rules: {
      ...typescript.configs.recommended.rules,
      ...typescript.configs['recommended-requiring-type-checking'].rules,
      
      // 严格的 TypeScript 规则
      '@typescript-eslint/no-explicit-any': 'error',
      '@typescript-eslint/no-unused-vars': 'error',
      '@typescript-eslint/explicit-function-return-type': 'error',
      '@typescript-eslint/no-non-null-assertion': 'warn',
      '@typescript-eslint/prefer-nullish-coalescing': 'error',
      '@typescript-eslint/prefer-optional-chain': 'error',
      '@typescript-eslint/no-unnecessary-type-assertion': 'error',
      '@typescript-eslint/no-unnecessary-condition': 'error',
      '@typescript-eslint/strict-boolean-expressions': 'warn',
    }
  },
  
  // 全局配置
  {
    files: ['**/*.js', '**/*.ts', '**/*.vue'],
    languageOptions: {
      ecmaVersion: 'latest',
      sourceType: 'module',
      globals: {
        // Node.js 全局变量
        process: 'readonly',
        Buffer: 'readonly',
        console: 'readonly',
        
        // 浏览器全局变量
        window: 'readonly',
        document: 'readonly',
        localStorage: 'readonly',
        sessionStorage: 'readonly',
        fetch: 'readonly',
        
        // Vite 全局变量
        import: 'readonly',
      }
    },
    rules: {
      // 通用代码质量规则
      'eqeqeq': 'error',
      'curly': 'error',
      'no-eval': 'error',
      'no-implied-eval': 'error',
      'no-new-func': 'error',
      'no-script-url': 'error',
      'no-self-compare': 'error',
      'no-sequences': 'error',
      'no-throw-literal': 'error',
      'no-void': 'error',
      'radix': 'error',
      'wrap-iife': 'error',
      'yoda': 'error',
      
      // 代码风格规则
      'array-bracket-spacing': ['error', 'never'],
      'block-spacing': ['error', 'always'],
      'brace-style': ['error', '1tbs', { allowSingleLine: true }],
      'comma-spacing': ['error', { before: false, after: true }],
      'comma-style': ['error', 'last'],
      'computed-property-spacing': ['error', 'never'],
      'func-call-spacing': ['error', 'never'],
      'indent': ['error', 2, { SwitchCase: 1 }],
      'key-spacing': ['error', { beforeColon: false, afterColon: true }],
      'keyword-spacing': ['error', { before: true, after: true }],
      'no-multiple-empty-lines': ['error', { max: 2, maxEOF: 1 }],
      'no-trailing-spaces': 'error',
      'object-curly-spacing': ['error', 'always'],
      'quotes': ['error', 'single', { avoidEscape: true }],
      'semi': ['error', 'always'],
      'semi-spacing': ['error', { before: false, after: true }],
      'space-before-blocks': ['error', 'always'],
      'space-before-function-paren': ['error', {
        anonymous: 'always',
        named: 'never',
        asyncArrow: 'always'
      }],
      'space-in-parens': ['error', 'never'],
      'space-infix-ops': 'error',
      'space-unary-ops': ['error', { words: true, nonwords: false }],
    }
  },
  
  // 忽略文件
  {
    ignores: [
      'node_modules/**',
      'dist/**',
      'build/**',
      '*.min.js',
      'coverage/**',
      '.vscode/**',
      '.idea/**',
      '*.d.ts'
    ]
  }
];