from __future__ import annotations

import re
from pathlib import Path

from ..engines import finding_id
from ..models import Finding,Location
from ..provenance import IGNORED_PARTS


PATTERNS=[
    ("container-latest-tag","Container image uses a mutable latest tag","low","supply-chain",re.compile(r"^\s*FROM\s+\S+:latest\b",re.I),"Mutable image tags make builds non-reproducible and can introduce unreviewed changes.","Pin the base image to an approved immutable digest.",{"Dockerfile"}),
    ("shell-download-execute","Downloaded content is executed directly","high","supply-chain",re.compile(r"(?:curl|wget).{0,200}\|\s*(?:sh|bash)\b"),"Executing network content without verification enables supply-chain compromise.","Download a pinned artifact, verify its signature or digest, then execute it separately.",{"Dockerfile",".sh",".yml",".yaml"}),
    ("k8s-privileged","Privileged container configuration","high","infrastructure",re.compile(r"\bprivileged\s*:\s*true\b",re.I),"Privileged containers substantially weaken workload isolation.","Remove privileged mode and grant only the specific capabilities required.",{ ".yml",".yaml"}),
    ("k8s-host-network","Host networking enabled","medium","infrastructure",re.compile(r"\bhostNetwork\s*:\s*true\b",re.I),"Host networking expands exposure and bypasses some network-isolation controls.","Disable host networking and apply explicit network policies.",{ ".yml",".yaml"}),
    ("github-write-all","Workflow grants write-all permissions","high","ci-security",re.compile(r"\bpermissions\s*:\s*write-all\b",re.I),"Broad workflow token permissions increase the impact of workflow compromise.","Declare least-privilege permissions per workflow and job.",{ ".yml",".yaml"}),
    ("github-unpinned-action","CI action uses a mutable branch reference","medium","supply-chain",re.compile(r"\buses\s*:\s*[^\s]+@(main|master|latest)\b",re.I),"Mutable action references can change without repository review.","Pin third-party actions to reviewed commit SHAs.",{ ".yml",".yaml"}),
    ("cors-wildcard","Wildcard CORS policy","medium","api-security",re.compile(r"(?:allow_origins|Access-Control-Allow-Origin|AllowedOrigins).{0,80}(?:\[?['\"]\*|\*)",re.I),"Wildcard cross-origin access can expose authenticated API responses to untrusted origins.","Allow only explicit trusted origins and review credential behavior.",{ ".py",".js",".ts",".go",".java"}),
    ("unsafe-inner-html","Potential unsafe HTML injection sink","high","frontend-security",re.compile(r"\.innerHTML\s*="),"Writing attacker-controlled HTML can create cross-site scripting.","Use textContent or a reviewed sanitization and templating boundary.",{ ".js",".ts",".jsx",".tsx"}),
    ("unlimited-token-approval","Unlimited token approval pattern","medium","wallet-security",re.compile(r"(?:MaxUint256|MAX_UINT256|2\s*\*\*\s*256\s*-\s*1)"),"Unlimited approvals increase loss if the spender is compromised.","Request the minimum required allowance and provide approval-revocation controls.",{ ".js",".ts",".jsx",".tsx"}),
]


def _scan(project: Path) -> tuple[list[Finding],dict]:
    findings=[]; scanned=0; dockerfiles=[]
    for path in project.rglob("*"):
        if not path.is_file(): continue
        relative=path.relative_to(project)
        if any(part in IGNORED_PARTS for part in relative.parts): continue
        if relative.parts and relative.parts[0] in {"tests","test","fixtures"}: continue
        kind="Dockerfile" if path.name.startswith("Dockerfile") else path.suffix.lower()
        try:
            if path.stat().st_size>2_000_000: continue
            lines=path.read_text(encoding="utf-8",errors="replace").splitlines()
        except OSError: continue
        scanned+=1; rel=relative.as_posix()
        if kind=="Dockerfile": dockerfiles.append((rel,lines))
        for number,line in enumerate(lines,1):
            for rule_id,title,severity,category,pattern,description,recommendation,kinds in PATTERNS:
                if kind not in kinds or not pattern.search(line): continue
                findings.append(Finding(finding_id(rule_id,rel,number,line),rule_id,title,severity,"medium",category,description,[Location(rel,number)],line.strip()[:500],recommendation,"full-stack-posture"))
    for rel,lines in dockerfiles:
        if not any(re.match(r"^\s*USER\s+",line,re.I) for line in lines):
            rule="container-root-default"; findings.append(Finding(finding_id(rule,rel,1,"missing USER"),rule,"Container has no non-root USER","medium","medium","infrastructure","Without a USER directive the container commonly runs as root.",[Location(rel,1)],"No USER directive found","Add a dedicated non-root USER in the final image stage.","full-stack-posture"))
    categories={name:sum(f.category==name for f in findings) for name in {"supply-chain","infrastructure","ci-security","api-security","frontend-security","wallet-security"}}
    return findings,{"files_scanned":scanned,"dockerfiles":len(dockerfiles),"findings_by_category":categories}


def _compliance(project: Path,frameworks: list[str],findings: list[Finding]) -> dict:
    has_workflows=(project/".github"/"workflows").is_dir(); has_monitoring=(project/"monitoring.toml").is_file(); has_suppressions=(project/".blockchain-auditor-suppressions.json").is_file()
    has_infrastructure=any(project.rglob("Dockerfile*")) or any(project.rglob("deployment.y*ml")) or any(project.rglob("k8s/**/*.y*ml"))
    has_application=any(path.suffix.lower() in {".py",".js",".ts",".jsx",".tsx",".go",".java"} and "tests" not in path.parts for path in project.rglob("*"))
    secure_gaps=[f.rule_id for f in findings if f.category in {"supply-chain","ci-security"}]; infrastructure_gaps=[f.rule_id for f in findings if f.category=="infrastructure"]; application_gaps=[f.rule_id for f in findings if f.category in {"api-security","frontend-security","wallet-security"}]
    evidence={
        "secure-development":{"status":"gap" if secure_gaps else "observed" if has_workflows else "not_assessed","evidence":["CI workflow directory present"] if has_workflows else [],"gaps":secure_gaps},
        "infrastructure-hardening":{"status":"gap" if infrastructure_gaps else "observed" if has_infrastructure else "not_assessed","evidence":["Infrastructure configuration present"] if has_infrastructure else [],"gaps":infrastructure_gaps},
        "application-security":{"status":"gap" if application_gaps else "observed" if has_application else "not_assessed","evidence":["Application source present"] if has_application else [],"gaps":application_gaps},
        "monitoring":{"status":"observed" if has_monitoring else "not_assessed","evidence":["monitoring.toml present"] if has_monitoring else [],"gaps":[] if has_monitoring else ["No configured monitoring rules found"]},
        "exception-management":{"status":"observed" if has_suppressions else "not_assessed","evidence":["Reasoned suppression file present"] if has_suppressions else [],"gaps":[]},
    }
    mappings=[]
    for framework in frameworks:
        if framework not in {"OWASP-SC","SOC2","ISO27001","PCI-DSS","GDPR","FATF"}: mappings.append({"framework":framework,"status":"unsupported","controls":[]}); continue
        relevant=[{"control":name,**value} for name,value in evidence.items()]
        mappings.append({"framework":framework,"status":"evidence_mapped","controls":relevant})
    return {"schema_version":"1.0","status":"completed","frameworks":mappings,"disclaimer":"This evidence mapping is not a certification, legal opinion, or determination of compliance. Controls require organizational and operational evidence beyond source review."}


def run_posture(project: Path,frameworks: list[str]) -> tuple[dict,dict,list[Finding]]:
    findings,summary=_scan(project)
    posture={"schema_version":"1.0","status":"completed","summary":summary,"findings":[finding.to_dict() for finding in findings],"limitations":["Pattern checks do not replace infrastructure configuration review, penetration testing, or runtime validation."]}
    return posture,_compliance(project,frameworks,findings),findings
