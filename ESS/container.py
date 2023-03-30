import itertools
import copy
from ESS import entity


class ContainerError(Exception):
    def __init__(self, cause):
        super().__init__(cause)
        self.cause = cause

    def __str__(self):
        return self.cause


class NotExistentItemError(ContainerError):
    pass


class DuplicateItemError(ContainerError):
    pass


class EmptyContainerError(ContainerError):
    def __str__(self):
        return "Container is empty"


class FactContainer:
    def __init__(self):
        self._facts = {}

    def __iter__(self):
        return iter(self._facts.values())

    def __getitem__(self, fact_name):
        try:
            return self._facts[fact_name]
        except KeyError:
            raise NotExistentItemError(fact_name)

    def __str__(self):
        l = ['Facts:']
        for fact in self._facts.values():
            l.append('\n%s' % fact)
        l.append("\n\nFacts count: %d" % len(self._facts))
        return ''.join(l)

    def __hash__(self):
        return hash(frozenset(self._facts.items()))

    def __eq__(self, other):
        return self._facts == other._facts

    def __bool__(self):
        return bool(self._facts)

    def get_facts_names(self):
        return frozenset(self._facts.keys())

    def add(self, fact):
        if not isinstance(fact, entity.Fact):
            raise ValueError(fact)
        if fact.name in self._facts:
            raise DuplicateItemError(str(fact))
        self._facts[fact.name] = fact

    def remove(self, fact_name):
        try:
            del self._facts[fact_name]
        except KeyError:
            raise NotExistentItemError(fact_name)

    def update(self, other):
        self._facts.update(other._facts)

    def clear(self):
        self._facts.clear()

    def copy(self):
        return copy.deepcopy(self)


class GoalContainer(FactContainer):
    def __str__(self):
        l = ['Goal:']
        for fact in self._facts.values():
            l.append('\n%s' % fact)
        return ''.join(l)


class RuleContainer(object):

    def __init__(self):
        self._rules = set()
        self._placeholder = {}
        self.unbinded = _UnbindedRuleContainer()

    def __iter__(self):
        return itertools.chain(iter(self._rules), iter(self.unbinded))

    def __len__(self):
        return len(self._rules) + len(self.unbinded)

    def __contains__(self, rule):
        return rule in self._rules

    def __nonzero__(self):
        return bool(self._rules) or bool(self.unbinded)

    def __str__(self):
        l = ['Rules:']
        for rule in self:
            l.append(str(rule))
        l.append("Rules count: %d" % len(self))
        return '\n\n'.join(l)

    def add(self, rule):
        if not isinstance(rule, entity.Rule):
            raise ValueError(rule)
        if rule.is_binded():
            if rule.name in self._rules:
                raise DuplicateItemError(rule.name)
            self._rules.add(rule)
            self._placeholder[rule.name] = rule
        else:
            self.unbinded.add(rule)

    def pop(self):
        if not self._rules:
            raise EmptyContainerError()
        return self._rules.pop()

    def remove(self, rule_name):
        rule = self._placeholder.get(rule_name, None) or self.unbinded._placeholder.get(rule_name, None)
        if not rule:
            raise NotExistentItemError(rule_name)
        if rule.is_binded():
            self._rules.remove(rule)
            del self._placeholder[rule.name]
        else:
            self.unbinded.remove(rule)

    def update(self, other):
        self._rules.update(other._rules)
        self.unbinded._rules.update(other.unbinded._rules)

    def clear(self):
        self._rules.clear()
        self.unbinded.clear()

    def copy(self):
        return copy.deepcopy(self)


class _UnbindedRuleContainer(RuleContainer):

    def __init__(self):
        self._rules = set()
        self._placeholder = {}

    def __iter__(self):
        return iter(self._rules)

    def __len__(self):
        return len(self._rules)

    def __nonzero__(self):
        return bool(self._rules)

    def add(self, rule):
        if rule.name in self._rules:
            raise DuplicateItemError(rule.name)
        self._rules.add(rule)
        self._placeholder[rule.name] = rule

    def clear(self):
        self._rules.clear()

    def remove(self, rule):
        self._rules.remove(rule)
        del self._placeholder[rule.name]
