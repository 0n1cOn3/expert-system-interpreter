from __future__ import division
import heapq, sys, time
from collections import deque
from ESS import entity, analyzer

class EngineError(Exception):
    def __init__(self, cause=''):
        super().__init__()
        self.cause = cause
    def __str__(self):
        return self.cause

class EmptyAgendaError(EngineError):
    def __str__(self):
        return 'pop from empty queue'

class WorkingMemory:
    def __init__(self, facts, rules, goal):
        self.initial_state = facts
        self.rules = rules
        self.goal = goal
    def __str__(self):
        return f"{self.initial_state}\n{self.rules}\n{self.goal}"

class Agenda:
    def __init__(self):
        self._queue = []
        self._consequents = set()
        self._priority = {}
        self._timer = time.clock if sys.platform == "win32" else time.time
    def __len__(self):
        return len(self._queue)
    def __iter__(self):
        return (el[1] for el in iter(self._queue))
    def __str__(self):
        return 'Agenda:\n' + '\n'.join(str(item[1]) for item in self._queue) + '\n'
    def __contains__(self, rule):
        return rule in self._consequents
    def is_empty(self):
        return not bool(self._queue)
    def push(self, rule):
        if not isinstance(rule, entity.Rule):
            raise ValueError(rule)
        if rule.consequent not in self._consequents:
            self._priority[rule.name] = -(self._timer())
            self._consequents.add(rule.consequent)
            heapq.heappush(self._queue, (self._priority[rule.name], rule))
    def pop(self):
        if not self._queue:
            raise EmptyAgendaError()
        rule = heapq.heappop(self._queue)[-1]
        self._consequents.remove(rule.consequent)
        return rule
    def clear(self):
        self._consequents.clear()
        self._priority.clear()
        del self._queue[:]

class Engine(object):

    def run(self, w_memory, search_fun, max_depth, h_fun=None, h_attrs=None, ):
        start_time = time.time()
        try:
            if h_fun:
                arrival_state, rules_applied, visited_cnt = search_fun(self, w_memory, max_depth, h_fun, h_attrs)
            else:
                arrival_state, rules_applied, visited_cnt = search_fun(self, w_memory, max_depth)
        except Exception:
            raise EngineError("Error with inference engine, maybe wrong heuristic attribute?")

        sec_elapsed = int(time.time()-start_time)
        if sec_elapsed > 60:
            min_elapsed = sec_elapsed // 60
            sec_elapsed %= 60
            time_elapsed_str = f"{min_elapsed} minutes, {sec_elapsed} seconds"
        else:
            time_elapsed_str = f"{sec_elapsed} seconds"

        if rules_applied:
            penetrance = len(rules_applied)/visited_cnt
            print(f"Initial state:\n{w_memory.initial_state}\n")
            print(f"Rule applied:\n\n{'\n\n'.join(map(str, rules_applied))}\n")
            print(f"Arrival state:\n{arrival_state}")
            print(f"\nSUCCESS\nPath length: {len(rules_applied)}\nPenetrance: {penetrance}\nVisited nodes count: {visited_cnt}\nTime elapsed: {time_elapsed_str}")
        else:
            print(f"Initial state:\n{w_memory.initial_state}\n")
            print(f"Arrival state:\n{arrival_state}")
            print(f"\nFAILURE\nVisited nodes count: {visited_cnt}\nTime elapsed: {time_elapsed_str}")

    def breadth_first_search(self, w_memory, max_depth):
        agenda = Agenda()
        open = deque([(w_memory.initial_state, [])])
        current_node = w_memory.initial_state
        closed = {w_memory.initial_state}
        visited_cnt = 0

        rules = analyzer.bind_rules(w_memory.rules, current_node)

        while open:
            if visited_cnt != 0 and visited_cnt % 100 == 0:
                print(f"Search in progress, visited nodes counter: {visited_cnt}")
            prev_node = current_node
            current_node, path = open.popleft()
            if current_node == w_memory.goal:
                return current_node, path, visited_cnt
            visited_cnt += 1
            if len(path) >= max_depth:
                continue

            if current_node.get_facts_names() != prev_node.get_facts_names():
                rules = analyzer.bind_rules(w_memory.rules, current_node)

            for rule in rules:
                rule = analyzer.evaluate_values(rule, current_node)
                if rule.antecedent(current_node):
                    agenda.push(rule)
            while not agenda.is_empty():
                rule_to_fire = agenda.pop()
                new_node = rule_to_fire.consequent(current_node)
                if new_node not in closed:
                    open.append((new_node, path+[rule_to_fire]))
                    closed.add(new_node)

        return current_node, None, visited_cnt
