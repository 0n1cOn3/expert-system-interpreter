import re
import operator
from ESS.parsing import parser


class BindError(Exception):
    def __init__(self, in_error):
        self.in_error = in_error
        super().__init__()

    def __str__(self):
        return self.in_error


class ValueEvaluatingError(BindError):
    pass


class NotNumericOperandError(BindError):
    pass


ARITHMETIC_OP_REX = re.compile(r'[\\+*/]|-(?!>)')
OPERATOR = {'+': operator.add,
            '-': operator.sub,
            '/': operator.truediv,
            '*': operator.mul}


def bind_rules(rules, facts):
    rules = rules.copy()
    while rules.unbinded:
        rule = rules.unbinded.pop()
        flag = True
        if rule.antecedent.is_binded():
            for conclusion in rule.consequent.conclusions:
                if not flag:
                    break
                if not conclusion.is_binded():
                    flag = False
                    for fact in facts:
                        new_rule = rule.copy()
                        var_name = conclusion.fact_name
                        _replace_same_varname(var_name, fact.name, new_rule)
                        rules.add(new_rule)
        else:
            for disjunction in rule.antecedent.disjunctions:
                if not flag:
                    break
                for condition in disjunction.conditions:
                    if not flag:
                        break
                    if not condition.is_binded():
                        flag = False
                        for fact in facts:
                            new_rule = rule.copy()

                            if '?' in condition.fact_name:
                                var_name = condition.fact_name
                            else:
                                var_name = re.findall(r'\?[\w_]+', condition.value)[0]

                            _replace_same_varname(var_name, fact.name, new_rule)
                            rules.add(new_rule)
    return rules


def _replace_same_varname(var_name, fact_name, rule):
    if not var_name.startswith('?'):
        raise ValueError('var_name: %s' % var_name)
    for disjunction in rule.antecedent.disjunctions:
        for condition in disjunction.conditions:
            if not condition.is_binded():
                if condition.fact_name == var_name:
                    condition.fact_name = fact_name
                if isinstance(condition.value, str) and '?' in condition.value:
                    condition.value = re.sub('\\'+var_name, fact_name, condition.value)
    for conclusion in rule.consequent.conclusions:
        if not conclusion.is_binded():
            if conclusion.fact_name == var_name:
                conclusion.fact_name = fact_name
            if len(conclusion.arg_list) == 2:
                conclusion.arg_list[1] = re.sub('\\'+var_name, fact_name, conclusion.arg_list[1])


def evaluate_values(rule, facts):
    # Evaluate the values of the rule's conditions
    values = []
    for condition in rule.conditions:
        value = condition.evaluate(facts)
        values.append(value)

    # Evaluate the rule's overall value based on the operator
    operator = rule.operator
    if operator == "AND":
        rule_value = all(values)
    elif operator == "OR":
        rule_value = any(values)

    return rule_value


def run_ruleset(ruleset, facts):
    # Initialize an empty list for activated rules
    activated_rules = []

    # Iterate over the rules and evaluate their values
    for rule in ruleset.rules:
        rule_value = evaluate_values(rule, facts)

        # If the rule's value is True, add it to the list of activated rules
        if rule_value:
            activated_rules.append(rule)

    # Execute the actions of the activated rules
    for rule in activated_rules:
        rule.execute_actions(facts)

class FactBase:
    def __init__(self):
        self.facts = {}

    def add_fact(self, fact):
        self.facts[fact.name] = fact

    def remove_fact(self, name):
        del self.facts[name]

    def get_fact(self, name):
        return self.facts.get(name)

    def get_all_facts(self):
        return self.facts.values()


class Fact:
    def __init__(self, name, slots):
        self.name = name
        self.slots = slots

    def __getitem__(self, slot_name):
        return self.slots[slot_name]

    def __setitem__(self, slot_name, value):
        self.slots[slot_name] = value

    def __repr__(self):
        return '{}({})'.format(self.name, ', '.join('{}={}'.format(k, v) for k, v in self.slots.items()))


class Slot:
    def __init__(self, name, value=None):
        self.name = name
        self.value = value

    def __repr__(self):
        return '{}={}'.format(self.name, self.value)


class Rule:
    def __init__(self, antecedent, consequent):
        self.antecedent = antecedent
        self.consequent = consequent

    def copy(self):
        return Rule(self.antecedent.copy(), self.consequent.copy())

    def __repr__(self):
        return '{} => {}'.format(self.antecedent, self.consequent)


class Antecedent:
    def __init__(self):
        self.disjunctions = []

    def copy(self):
        antecedent = Antecedent()
        antecedent.disjunctions = [disjunction.copy() for disjunction in self.disjunctions]
        return antecedent

    def add_disjunction(self, disjunction):
        self.disjunctions.append(disjunction)

    def is_binded(self):
        for disjunction in self.disjunctions:
            for condition in disjunction.conditions:
                if not condition.is_binded():
                    return False
        return True

    def __repr__(self):
        return ' | '.join('({})'.format(disjunction) for disjunction in self.disjunctions)


class Consequent:
    def __init__(self):
        self.conclusions = []

    def copy(self):
        consequent = Consequent()
        consequent.conclusions = [conclusion.copy() for conclusion in self.conclusions]
        return consequent

    def add_conclusion(self, conclusion):
        self.conclusions.append(conclusion)

    def is_binded(self):
        for conclusion in self.conclusions:
            if not conclusion.is_binded():
                return False
        return True

    def __repr__(self):
        return ', '.join(str(conclusion) for conclusion in self.conclusions)


class Disjunction:
    def __init__(self):
        self.conditions = []

    def copy(self):
        disjunction = Disjunction()
        disjunction.conditions = [condition.copy() for condition in self.conditions]
        return disjunction

    def add_condition(self, condition):
        self.conditions.append(condition)

    def is_binded(self):
        for condition in self.conditions:
            if not condition.is_binded():
                return False
        return True

    def __repr__(self):
        return ' & '.join(str(condition) for condition in self.conditions)


class Condition:
    """A boolean condition for a rule."""

    def __init__(self, fact, value):
        self.fact = fact
        self.value = value

    def __call__(self, *args, **kwargs):
        """Evaluate the condition with a set of facts."""
        return self.fact(*args, **kwargs) == self.value
