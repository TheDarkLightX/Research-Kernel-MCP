//! Write cross-check vectors for Python ports of two Zeno-ADP 0.8.0 queries:
//! `robust_prefix::{zero_regret, within_budget}` and `common_optimum::common`.
//! Each case records its inputs and Zeno-ADP's answers. Output is JSON on stdout.

use num_bigint::BigUint;
use zeno_adp::common_optimum::{common, Costed, ModelSet};
use zeno_adp::robust_prefix::{state_bound, within_budget, zero_regret, Step};
use zeno_adp::Chart;

struct Lcg(u64);
impl Lcg {
    fn next(&mut self) -> u64 {
        self.0 = self.0.wrapping_mul(6364136223846793005).wrapping_add(1442695040888963407);
        self.0 >> 33
    }
    fn below(&mut self, n: u64) -> u64 {
        self.next() % n
    }
}

fn rules_json(rules: &[(usize, usize)]) -> String {
    let items: Vec<String> = rules.iter().map(|(c, r)| format!("[{c},{r}]")).collect();
    format!("[{}]", items.join(","))
}

fn ints<T: std::fmt::Display>(values: &[T]) -> String {
    let items: Vec<String> = values.iter().map(|v| v.to_string()).collect();
    format!("[{}]", items.join(","))
}

fn plan_case(rng: &mut Lcg, case: usize) -> String {
    let large = case >= 80;
    let worlds = 1 + rng.below(if large { 4 } else { 3 }) as usize;
    let n = 1 + rng.below(if large { 8 } else { 5 }) as usize;
    let mut cells = Vec::new();
    let mut spec = Vec::new();
    for cell in 0..n {
        let count = 1 + rng.below(if large { 4 } else { 3 }) as usize;
        let mut rules = Vec::new();
        let mut rule_spec = Vec::new();
        for index in 0..count {
            let costs: Vec<i64> = (0..worlds).map(|_| rng.below(7) as i64).collect();
            let credit = rng.below(4);
            let finish = cell == 0 || (index == 0 && rng.below(2) == 0) || rng.below(3) == 0;
            if finish {
                rules.push(Step::finish(costs.clone(), credit));
                rule_spec.push(format!("{{\"costs\":{},\"credit\":{credit},\"child\":null}}", ints(&costs)));
            } else {
                let child = rng.below(cell as u64) as usize;
                rules.push(Step::to(costs.clone(), credit, child));
                rule_spec.push(format!("{{\"costs\":{},\"credit\":{credit},\"child\":{child}}}", ints(&costs)));
            }
        }
        cells.push(rules);
        spec.push(format!("[{}]", rule_spec.join(",")));
    }
    let root = n - 1;
    let chart = Chart::new(cells, root).expect("valid chart");
    let zero = zero_regret(&chart, worlds).expect("zero regret").into_inner();
    let budget: Vec<BigUint> = (0..worlds).map(|_| BigUint::from(rng.below(4))).collect();
    let limit = usize::try_from(state_bound(&chart, &budget)).expect("small");
    let within = within_budget(&chart, worlds, &budget, limit).expect("within").into_inner();
    let common_plan = match &zero.common_plan {
        Some(plan) => rules_json(plan),
        None => "null".to_string(),
    };
    let completions: Vec<String> = zero.completions.iter().map(|p| rules_json(p)).collect();
    format!(
        "{{\"case\":{case},\"worlds\":{worlds},\"root\":{root},\"cells\":[{}],\"budget\":{},\
         \"zero_regret\":{{\"best_credit\":{},\"count\":\"{}\",\"prefix\":{},\"common_plan\":{},\"completions\":[{}]}},\
         \"within_budget\":{{\"best\":{},\"count\":\"{}\",\"prefix\":{},\"regret\":{}}}}}",
        spec.join(","),
        ints(&budget),
        zero.best_credit(root),
        zero.count(root),
        rules_json(&zero.prefix),
        common_plan,
        completions.join(","),
        within.best,
        within.count,
        rules_json(&within.prefix),
        ints(&within.regret),
    )
}

fn common_case(rng: &mut Lcg, case: usize) -> String {
    let models = 1 + rng.below(4) as usize;
    let count = 1 + rng.below(6) as usize;
    let mut rules = Vec::new();
    let mut spec = Vec::new();
    for _ in 0..count {
        let costs: Vec<i64> = (0..models).map(|_| rng.below(5) as i64 - 2).collect();
        rules.push(Costed::rule(costs.clone(), []));
        spec.push(ints(&costs));
    }
    let chart = Chart::new(vec![rules], 0).expect("valid chart");
    let mut selections: Vec<Vec<usize>> = vec![(0..models).collect()];
    let mask = 1 + rng.below((1u64 << models) - 1);
    selections.push((0..models).filter(|m| mask >> m & 1 == 1).collect());
    let mut answers = Vec::new();
    for selection in selections {
        let set = ModelSet::new(selection.clone(), models).expect("models");
        let answer = common(&chart, models, &set).expect("common");
        let answer = answer.as_ref();
        let first = match answer.witness(&chart, &BigUint::from(0u32)).expect("witness") {
            Some(w) => w.preorder[0].1.to_string(),
            None => "null".to_string(),
        };
        answers.push(format!(
            "{{\"models\":{},\"exists\":{},\"count\":\"{}\",\"first\":{first}}}",
            ints(&selection),
            answer.exists(),
            answer.count()
        ));
    }
    format!("{{\"case\":{case},\"models\":{models},\"costs\":[{}],\"answers\":[{}]}}", spec.join(","), answers.join(","))
}

/// Read plan charts as whitespace-separated integers: for each chart `worlds root cells`,
/// then per cell `rules`, then per rule `credit child costs...` (child -1 finishes), then
/// one budget per world.
fn stdin_cases() -> Vec<String> {
    use std::io::Read;
    let mut text = String::new();
    std::io::stdin().read_to_string(&mut text).expect("stdin");
    let mut it = text.split_whitespace().map(|t| t.parse::<i64>().expect("integer"));
    let mut out = Vec::new();
    let mut case = 1000;
    while let Some(worlds) = it.next() {
        let worlds = worlds as usize;
        let root = it.next().unwrap() as usize;
        let n = it.next().unwrap() as usize;
        let mut cells = Vec::new();
        let mut spec = Vec::new();
        for _ in 0..n {
            let count = it.next().unwrap() as usize;
            let mut rules = Vec::new();
            let mut rule_spec = Vec::new();
            for _ in 0..count {
                let credit = it.next().unwrap() as u64;
                let child = it.next().unwrap();
                let costs: Vec<i64> = (0..worlds).map(|_| it.next().unwrap()).collect();
                if child < 0 {
                    rules.push(Step::finish(costs.clone(), credit));
                    rule_spec.push(format!("{{\"costs\":{},\"credit\":{credit},\"child\":null}}", ints(&costs)));
                } else {
                    rules.push(Step::to(costs.clone(), credit, child as usize));
                    rule_spec.push(format!("{{\"costs\":{},\"credit\":{credit},\"child\":{child}}}", ints(&costs)));
                }
            }
            cells.push(rules);
            spec.push(format!("[{}]", rule_spec.join(",")));
        }
        let budget: Vec<BigUint> = (0..worlds).map(|_| BigUint::from(it.next().unwrap() as u64)).collect();
        let chart = Chart::new(cells, root).expect("valid chart");
        out.push(solve(&chart, worlds, root, &spec, &budget, case));
        case += 1;
    }
    out
}

fn solve(chart: &Chart<Step>, worlds: usize, root: usize, spec: &[String], budget: &[BigUint], case: usize) -> String {
    let zero = zero_regret(chart, worlds).expect("zero regret").into_inner();
    let limit = usize::try_from(state_bound(chart, budget)).expect("small");
    let within = within_budget(chart, worlds, budget, limit).expect("within").into_inner();
    let common_plan = match &zero.common_plan {
        Some(plan) => rules_json(plan),
        None => "null".to_string(),
    };
    let completions: Vec<String> = zero.completions.iter().map(|p| rules_json(p)).collect();
    format!(
        "{{\"case\":{case},\"worlds\":{worlds},\"root\":{root},\"cells\":[{}],\"budget\":{},\
         \"zero_regret\":{{\"best_credit\":{},\"count\":\"{}\",\"prefix\":{},\"common_plan\":{},\"completions\":[{}]}},\
         \"within_budget\":{{\"best\":{},\"count\":\"{}\",\"prefix\":{},\"regret\":{}}}}}",
        spec.join(","),
        ints(budget),
        zero.best_credit(root),
        zero.count(root),
        rules_json(&zero.prefix),
        common_plan,
        completions.join(","),
        within.best,
        within.count,
        rules_json(&within.prefix),
        ints(&within.regret),
    )
}

fn main() {
    if std::env::args().any(|a| a == "--stdin") {
        println!("[{}]", stdin_cases().join(",\n"));
        return;
    }
    let mut rng = Lcg(0x5eed_2026_1125);
    let plans: Vec<String> = (0..120).map(|i| plan_case(&mut rng, i)).collect();
    let commons: Vec<String> = (0..80).map(|i| common_case(&mut rng, i)).collect();
    println!(
        "{{\"schema\":\"zeno-adp-vectors/1\",\"zeno_adp\":\"0.8.0\",\"robust_prefix\":[{}],\"common_optimum\":[{}]}}",
        plans.join(",\n"),
        commons.join(",\n")
    );
}
