# SecureBananaLabs — Job Budget Runtime Proof

Gerado em: 2026-07-17T11:34:16.387844+00:00

## Resultado

- Decisão: **BLOCKED_MODULE_LOAD**
- Confiança: **35.0**
- Runtime status: **module_load_failed**
- Bug confirmado: **não**
- Próxima ação: **inspect_module_format_and_dependencies**

## Hipótese

`budgetMin` maior que `budgetMax` pode ser aceito pelo validator de criação de jobs.

## Evidência estática

- `budgetMin` presente: **sim**
- `budgetMax` presente: **sim**
- Validação cruzada detectada: **não**

## Execução local

- Módulo carregado: **não**
- `node_modules` encontrado: **não**
- Código-fonte alterado: **não**
- Dependências instaladas: **não**
- Publicação externa: **não**

## Schemas testados

- Nenhum schema foi executado.
## Erro de carregamento

```text
{
  "name": "Error",
  "message": "Cannot find package 'zod' imported from C:\\Users\\AP10\\Revenue-Workspaces\\SecureBananaLabs-bug-bounty-743\\repository\\apps\\api\\src\\validators\\job.js",
  "stack": "Error [ERR_MODULE_NOT_FOUND]: Cannot find package 'zod' imported from C:\\Users\\AP10\\Revenue-Workspaces\\SecureBananaLabs-bug-bounty-743\\repository\\apps\\api\\src\\validators\\job.js\n    at Object.getPackageJSONURL (node:internal/modules/package_json_reader:301:9)\n    at packageResolve (node:internal/modules/esm/resolve:768:81)\n    at moduleResolve (node:internal/modules/esm/resolve:859:18)\n    at defaultResolve (node:internal/modules/esm/resolve:992:11)\n    at #cachedDefaultResolve (node:internal/modules/esm/loader:691:20)\n    at #resolveAndMaybeBlockOnLoaderThread (node:internal/modules/esm/loader:708:38)\n    at ModuleLoader.resolveSync (node:internal/modules/esm/loader:740:52)\n    at #resolve (node:internal/modules/esm/loader:673:17)\n    at ModuleLoader.getOrCreateModuleJob (node:internal/modules/esm/loader:593:35)\n    at ModuleJob.syncLink (node:internal/modules/esm/module_job:163:33)"
}
```

## Segurança operacional

- Código do repositório alterado: **não**
- Instalação de dependências realizada: **não**
- Issue criada: **não**
- Comentário publicado: **não**
- Fork criado: **não**
- Pull request criado: **não**