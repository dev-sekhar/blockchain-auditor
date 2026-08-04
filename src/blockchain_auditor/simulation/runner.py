from __future__ import annotations

import tomllib
from decimal import Decimal, InvalidOperation, getcontext
from pathlib import Path

from ..config import AuditConfig

getcontext().prec = 40


def _decimal(value, name: str) -> Decimal:
    try: result=Decimal(str(value))
    except InvalidOperation as exc: raise ValueError(f"{name} must be numeric") from exc
    if not result.is_finite(): raise ValueError(f"{name} must be finite")
    return result


def load_scenarios(project: Path, filename: str) -> tuple[list[dict], str | None]:
    path=Path(filename)
    if not path.is_absolute(): path=project/path
    if not path.exists(): return [],None
    try:
        with path.open("rb") as stream: data=tomllib.load(stream)
    except (OSError,tomllib.TOMLDecodeError) as exc: raise ValueError(f"Invalid scenario specification {path}: {exc}") from exc
    scenarios=data.get("scenarios",[])
    if not isinstance(scenarios,list): raise ValueError("Scenario file must use [[scenarios]] entries")
    ids=set()
    for item in scenarios:
        if not isinstance(item,dict) or not item.get("id") or not item.get("type"): raise ValueError("Every scenario requires id and type")
        if item["id"] in ids: raise ValueError(f"Duplicate scenario ID: {item['id']}")
        ids.add(item["id"])
    return scenarios,str(path)


def _amm(item: dict) -> dict:
    reserve_in=_decimal(item.get("reserve_in"),"reserve_in"); reserve_out=_decimal(item.get("reserve_out"),"reserve_out"); amount=_decimal(item.get("amount_in"),"amount_in"); fee=_decimal(item.get("fee_bps",30),"fee_bps")
    if min(reserve_in,reserve_out,amount)<=0 or not 0<=fee<10000: raise ValueError("AMM reserves/amount must be positive and fee_bps between 0 and 9999")
    effective=amount*(Decimal(10000)-fee)/Decimal(10000); output=reserve_out*effective/(reserve_in+effective)
    spot=reserve_out/reserve_in; execution=output/amount; impact=(spot-execution)/spot*100
    limit=_decimal(item.get("max_price_impact_pct",5),"max_price_impact_pct"); breached=impact>limit
    return {"status":"breach" if breached else "within_limit","severity":"high" if impact>20 else "medium","metrics":{"amount_out":str(output),"spot_price":str(spot),"execution_price":str(execution),"price_impact_pct":str(impact),"constant_product":str(reserve_in*reserve_out)},"threshold":{"max_price_impact_pct":str(limit)},"message":f"AMM price impact is {impact:.4f}% (limit {limit}%)."}


def _oracle(item: dict) -> dict:
    collateral=_decimal(item.get("collateral_value"),"collateral_value"); debt=_decimal(item.get("debt"),"debt"); threshold=_decimal(item.get("liquidation_threshold",0.8),"liquidation_threshold"); shock=_decimal(item.get("shock_pct"),"shock_pct")
    if collateral<0 or debt<=0 or not 0<threshold<=1 or not 0<=shock<=100: raise ValueError("Invalid oracle-shock parameters")
    shocked=collateral*(Decimal(1)-shock/100); health=shocked*threshold/debt; breached=health<1
    return {"status":"breach" if breached else "within_limit","severity":"critical" if health<Decimal("0.8") else "high","metrics":{"shocked_collateral_value":str(shocked),"health_factor":str(health)},"threshold":{"minimum_health_factor":"1"},"message":f"Post-shock health factor is {health:.4f}."}


def _governance(item: dict) -> dict:
    shares=[_decimal(value,"voting_shares") for value in item.get("voting_shares",[])]
    if not shares or any(value<0 for value in shares) or sum(shares)<=0: raise ValueError("voting_shares must contain positive voting weights")
    concentration=max(shares)/sum(shares)*100; limit=_decimal(item.get("max_holder_pct",33.34),"max_holder_pct"); breached=concentration>=limit
    return {"status":"breach" if breached else "within_limit","severity":"high","metrics":{"largest_holder_pct":str(concentration),"participants":len(shares)},"threshold":{"max_holder_pct":str(limit)},"message":f"Largest voting holder controls {concentration:.4f}%."}


def _bridge(item: dict) -> dict:
    validators=int(item.get("validators",0)); threshold=int(item.get("signature_threshold",0)); compromised=int(item.get("compromised_validators",0))
    if validators<=0 or not 1<=threshold<=validators or not 0<=compromised<=validators: raise ValueError("Invalid bridge quorum parameters")
    breached=compromised>=threshold; margin=threshold-compromised
    return {"status":"breach" if breached else "within_limit","severity":"critical","metrics":{"validators":validators,"signature_threshold":threshold,"compromised_validators":compromised,"remaining_security_margin":margin},"threshold":{"minimum_margin":1},"message":f"Bridge quorum security margin is {margin} validator(s)."}


MODELS={"amm_swap":_amm,"oracle_shock":_oracle,"governance_concentration":_governance,"bridge_quorum":_bridge}


def run_simulations(project: Path, config: AuditConfig) -> dict:
    scenarios,path=load_scenarios(project,config.scenarios_file)
    if not config.economic_simulation: return {"schema_version":"1.0","requested":False,"status":"not_requested","scenarios_file":path,"results":[],"summary":{"total":0,"breaches":0,"errors":0},"limitations":["No economic scenarios were executed."]}
    if not scenarios: return {"schema_version":"1.0","requested":True,"status":"no_scenarios","scenarios_file":path,"results":[],"summary":{"total":0,"breaches":0,"errors":0},"limitations":["Create audit-scenarios.toml to execute deterministic models."]}
    results=[]
    for item in scenarios:
        model=MODELS.get(item["type"])
        if not model: results.append({"id":item["id"],"type":item["type"],"status":"error","severity":"medium","message":"Unsupported scenario type"}); continue
        try: result=model(item); results.append({"id":item["id"],"type":item["type"],"assumptions":item,**result})
        except (ValueError,TypeError) as exc: results.append({"id":item["id"],"type":item["type"],"status":"error","severity":"medium","message":str(exc)})
    breaches=sum(item["status"]=="breach" for item in results); errors=sum(item["status"]=="error" for item in results)
    return {"schema_version":"1.0","requested":True,"status":"completed" if not errors else "completed_with_errors","scenarios_file":path,"results":results,"summary":{"total":len(results),"breaches":breaches,"errors":errors},"limitations":["These deterministic models do not execute project bytecode or reproduce live-chain state.","Results depend entirely on declared assumptions and thresholds."]}
