#!/usr/bin/env node
'use strict';

// Registry-level import guard. Run this against the pinned isolated n8n runtime
// before importing a release workflow. It intentionally reads no credentials.
const fs = require('fs');
const path = require('path');

const root = path.resolve(__dirname, '..');
const runtime = path.resolve(process.argv[2] || path.join(root, '.n8n-runtime'));
const workflowPath = path.resolve(process.argv[3] || path.join(root, 'n8n', 'Localle_Option_B_Reservation_Intake_FINAL.n8n.json'));
const runtimeModules = path.join(runtime, 'node_modules');

function readJson(file) {
  return JSON.parse(fs.readFileSync(file, 'utf8'));
}

function packageRegistry(packageName) {
  const packageRoot = path.join(runtimeModules, packageName);
  return {
    packageRoot,
    known: readJson(path.join(packageRoot, 'dist', 'known', 'nodes.json')),
  };
}

function versionIsAdvertised(nodeType, version) {
  const advertised = nodeType.description?.version;
  return Array.isArray(advertised) ? advertised.includes(version) : advertised === version;
}

function selectedTypeIsExecutableOrSubNode(nodeType) {
  return Boolean(nodeType?.execute || nodeType?.trigger || nodeType?.poll || nodeType?.webhook || nodeType?.supplyData);
}

const exported = readJson(workflowPath);
// `n8n export:workflow --id` emits a one-element array, while an import
// artifact is an object. Treat both representations identically.
const workflow = Array.isArray(exported) ? exported[0] : exported;
if (!workflow || !Array.isArray(workflow.nodes)) {
  throw new Error(`Workflow at ${workflowPath} is neither a workflow object nor a one-item export array`);
}
const { NodeHelpers } = require(path.join(runtimeModules, 'n8n-workflow'));
const registries = {
  'n8n-nodes-base': packageRegistry('n8n-nodes-base'),
  '@n8n/n8n-nodes-langchain': packageRegistry('@n8n/n8n-nodes-langchain'),
};
const runtimeVersion = readJson(path.join(runtimeModules, 'n8n', 'package.json')).version;
const errors = [];

for (const node of workflow.nodes) {
  const packageName = node.type.startsWith('@n8n/') ? '@n8n/n8n-nodes-langchain' : 'n8n-nodes-base';
  const shortName = node.type.split('.').at(-1);
  const registry = registries[packageName];
  const entry = registry.known[shortName];
  if (!entry) {
    errors.push(`${node.name}: ${node.type} is not registered by ${packageName}`);
    continue;
  }
  const modulePath = path.join(registry.packageRoot, entry.sourcePath);
  const NodeClass = require(modulePath)[entry.className];
  const declaredType = new NodeClass();
  const selectedType = NodeHelpers.getVersionedNodeType(declaredType, node.typeVersion);
  if (!selectedType) {
    errors.push(`${node.name}: ${node.type}@${node.typeVersion} resolves to undefined`);
    continue;
  }
  if (!versionIsAdvertised(selectedType, node.typeVersion)) {
    errors.push(`${node.name}: ${node.type}@${node.typeVersion} is not advertised by n8n ${runtimeVersion}`);
    continue;
  }
  if (!selectedTypeIsExecutableOrSubNode(selectedType)) {
    errors.push(`${node.name}: ${node.type}@${node.typeVersion} has no runtime implementation`);
    continue;
  }
  const operation = node.parameters?.operation;
  if (operation) {
    const operationOptions = (selectedType.description?.properties || [])
      .filter((property) => property.name === 'operation')
      .flatMap((property) => property.options || [])
      .map((option) => option.value);
    if (operationOptions.length && !operationOptions.includes(operation)) {
      errors.push(`${node.name}: operation ${operation} is unavailable for ${node.type}@${node.typeVersion}`);
      continue;
    }
  }
  const credentialTypes = (selectedType.description?.credentials || []).map((credential) => credential.name);
  console.log(`PASS\t${node.name}\t${node.type}@${node.typeVersion}\timpl=${selectedType.execute ? 'execute' : selectedType.trigger ? 'trigger' : selectedType.poll ? 'poll' : selectedType.supplyData ? 'supplyData' : 'webhook'}\tcredentials=${credentialTypes.join(',') || '-'}`);
}

if (errors.length) {
  console.error(`FAIL — ${errors.length} n8n ${runtimeVersion} compatibility error(s)`);
  for (const error of errors) console.error(error);
  process.exitCode = 1;
} else {
  console.log(`PASS — ${workflow.nodes.length} workflow nodes are registered, version-compatible, and implemented in n8n ${runtimeVersion}`);
}
