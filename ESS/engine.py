from __future__ import division
import heapq
from collections import deque
import time
import sys
from twitter.api import _DEFAULT
from ESS import entity
from ESS import analyzer


class EngineError(Exception):
    def __init__(self, cause=''):
        Exception.__init__(self)
        self.cause = cause

    def __str__(self):
        return self.cause

class EmptyAgendaError(EngineError):
    def __str__(self):
        return 'pop from empty queue'


class WorkingMemory(object):

    def __init__(self, facts, rules, goal):
        self.initial_state = facts
        self.rules = rules
        self.goal = goal

    def __str__(self):
        return "%s\n%s\n%s" % (self.initial_state, self.rules, self.goal)


class Agenda(object):

    def __init__(self):
        self._queue = []
        self._consequents = set()
        self._priority = {}
        if sys.platform == "win32":
            self._timer = time.clock
        else:
            self._timer = time.time

    def __len__(self):
        return len(self._queue)

    def __iter__(self):
        return (el[1] for el in iter(self._queue))

    def __str__(self):
        l = ['Agenda:']
        for item in self._queue:
            l.append(str(item[1])+'\n')
        return '\n'.join(l)

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
            min_elapsed = sec_elapsed//60
            sec_elapsed %= 60
            time_elapsed_str = "%s minutes, %s seconds" % (min_elapsed, sec_elapsed)
        else:
            time_elapsed_str = "%s seconds" % sec_elapsed

        if rules_applied:
            penetrance = len(rules_applied)/visited_cnt
            print "Initial state:\n%s\n" % w_memory.initial_state
            print "Rule applied:\n\n%s\n" % '\n\n'.join(map(str, rules_applied))
            print "Arrival state:\n%s" % arrival_state
            print "\nSUCCESS\nPath length: %s\nPenetrance: %s\nVisited nodes count: %s\nTime elapsed: %s" % \
                    (len(rules_applied), str(penetrance), str(visited_cnt), time_elapsed_str)
        else:
            print "Initial state:\n%s\n" % w_memory.initial_state
            print "Arrival state:\n%s" % arrival_state
            print "\nFAILURE\nVisited nodes count: %s\nTime elapsed: %s" % (visited_cnt, time_elapsed_str)

    def breadth_first_search(self, w_memory, max_depth):
        agenda = Agenda()
        open = deque([(w_memory.initial_state, [])])
        current_node = w_memory.initial_state
        closed = {w_memory.initial_state}
        visited_cnt = 0

        rules = analyzer.bind_rules(w_memory.rules, current_node)

        while open:
            if visited_cnt != 0 and visited_cnt % 100 == 0:
                print "Search in progress, visited nodes counter: %s" % visited_cnt
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
                    open.append( (new_node, path+[rule_to_fire]) )
                    closed.add(new_node)

        return current_node, None, visited_cnt

    def depth_first_search(self, w_memory, max_depth):
        agenda = Agenda()
        open = [(w_memory.initial_state, [])]
        current_node = w_memory.initial_state
        closed = {w_memory.initial_state}
        visited_cnt = 0

        rules = analyzer.bind_rules(w_memory.rules, current_node)

        while open:
            if visited_cnt != 0 and visited_cnt % 100 == 0:
                print "Search in progress, visited nodes counter: %s" % visited_cnt
            prev_node = current_node
            current_node, path = open.pop()
            if current_node == w_memory.goal:
                return current_node, path, visited_cnt
            visited_cnt += 1
            if len(path) > max_depth-1:
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
                    open.append( (new_node, path+[rule_to_fire]) )
                    closed.add(new_node)

        return current_node, None, visited_cnt

    def a_star_search(self, w_memory, max_depth, h_fun=None, h_attrs=None):
        agenda = Agenda()
        if h_attrs:
            priority = h_fun(self, w_memory.initial_state, w_memory.goal, h_attrs)
        else:
            priority = h_fun(self, w_memory.initial_state, w_memory.goal)

        open = [(priority, (w_memory.initial_state, []))]
        current_node = w_memory.initial_state
        closed = {w_memory.initial_state}
        visited_cnt = 0

        rules = analyzer.bind_rules(w_memory.rules, current_node)

        while open:
            if visited_cnt != 0 and visited_cnt % 100 == 0:
                print "Search in progress, visited nodes counter: %s" % visited_cnt
            prev_node = current_node
            current_node, path = heapq.heappop(open)[-1]
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
                    closed.add(new_node)
                    if h_attrs:
                        priority = len(path) + h_fun(self, current_node, w_memory.goal, h_attrs)
                    else:
                        priority = len(path) + h_fun(self, current_node, w_memory.goal)
                    heapq.heappush(open, (priority, (new_node, path+[rule_to_fire])))

        return current_node, None, visited_cnt

    def best_first_search(self, w_memory, max_depth, h_fun=None, h_attrs=None):
        agenda = Agenda()
        if h_attrs:
            priority = h_fun(self, w_memory.initial_state, w_memory.goal, h_attrs)
        else:
            priority = h_fun(self, w_memory.initial_state, w_memory.goal)

        open = [(priority, (w_memory.initial_state, []))]
        current_node = w_memory.initial_state
        closed = {w_memory.initial_state}
        visited_cnt = 0

        rules = analyzer.bind_rules(w_memory.rules, current_node)

        while open:
            if visited_cnt != 0 and visited_cnt % 100 == 0:
                print "Search in progress, visited nodes counter: %s" % visited_cnt
            prev_node = current_node
            current_node, path = heapq.heappop(open)[-1]
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
                    closed.add(new_node)
                    if h_attrs:
                        priority = h_fun(self, current_node, w_memory.goal, h_attrs)
                    else:
                        priority = h_fun(self, current_node, w_memory.goal)
                    heapq.heappush(open, (priority, (new_node, path+[rule_to_fire])))

        return current_node, None, visited_cnt

    def h_hamming_distance(self, node, goal):
        distance = 0
        for fact in node:
            if fact != goal[fact.name]:
                distance += 1
        return distance

    def h_manhattan_distance(self, node, goal, h_attrs):
        value, x, y = h_attrs
        distance = 0
        for fact in node:
            for goal_fact in goal:
                if fact[value] == goal_fact[value]:
                    distance = distance + abs(fact[x]-goal_fact[x]) + abs(fact[y]-goal_fact[y])
        return distance

    def h_linear_conflict(self, node, goal, h_attrs):
        value, x, y = h_attrs
        conflicts = 0
        rows = {}
        for fact in node:
            for goal_fact in goal:
                if fact[value] == goal_fact[value]:
                    if fact[x] == goal_fact[x] and fact[y] != goal_fact[y]:
                        try:
                            row = rows[fact[x]]
                        except KeyError:
                            row = {}
                            rows[fact[x]] = row
                        offset = abs(fact[y]-goal_fact[y])
                        try:
                            row[offset] += 1
                        except KeyError:
                            row[offset] = 1
        for i in rows:
            row = rows[i]
            for offset in row:
                if row[offset] == 2:
                    conflicts += 1
        return self.h_manhattan_distance(node, goal, h_attrs) + conflicts*2