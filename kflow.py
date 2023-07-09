#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
 Authors:
   yifengyou <842056007@qq.com>
"""

import argparse
import csv
import datetime
import json
import logging
import multiprocessing
import os
import os.path
import sqlite3
import sys

CURRENT_VERSION = "0.1.0"

"""
VCG（Visualization of Compiler Graphs）

VCG是一种可视化编译器图的工具，它可以读取一个文本格式的图的规范，并将图显示出来。
如果图中的节点的位置不是全部固定的，VCG可以使用一些启发式算法来布局图，以减少交叉、最小化边的长度、居中节点等1。

样例格式：

graph: { title: "hello.c"
node: { title: "func1" label: "func1\nhello.c:3:6" }
node: { title: "puts" label: "__builtin_puts\n<built-in>" shape : ellipse }
edge: { sourcename: "func1" targetname: "puts" label: "hello.c:5:2" }
node: { title: "func2" label: "func2\nhello.c:7:6" }
edge: { sourcename: "func2" targetname: "func1" label: "hello.c:9:2" }
edge: { sourcename: "func2" targetname: "puts" label: "hello.c:10:2" }
node: { title: "func3" label: "func3\nhello.c:12:6" }
edge: { sourcename: "func3" targetname: "func2" label: "hello.c:14:2" }
edge: { sourcename: "func3" targetname: "puts" label: "hello.c:15:2" }
node: { title: "func4" label: "func4\nhello.c:17:6" }
edge: { sourcename: "func4" targetname: "func3" label: "hello.c:19:2" }
edge: { sourcename: "func4" targetname: "puts" label: "hello.c:20:2" }
node: { title: "main" label: "main\nhello.c:24:6" }
edge: { sourcename: "main" targetname: "func4" label: "hello.c:26:2" }
}
"""


class VCGParser(object):
    def parse_file(self, filename):
        with open(filename, 'r') as f:
            vcg_string = f.readlines()
        return self.parse_string(vcg_string)

    def format_graph(self, str):
        return str.replace("graph: ", ""). \
                   replace("graph: ", '"graph": '). \
                   replace(" title: ", ' "title": '). \
                   strip() + "}"

    def format_node(self, str):
        return str.replace("node: ", ""). \
            replace(" title: ", ' "title": '). \
            replace(" label: ", ', "label": '). \
            replace("shape : ellipse", ', "shape" : "ellipse" '). \
            strip()

    def format_edge(self, str):
        return str.replace("edge: ", ""). \
            replace(" sourcename: ", ' "sourcename": '). \
            replace(" targetname: ", ', "targetname": '). \
            replace(" label: ", ', "label": '). \
            strip()

    def parse_string(self, vcg_string):
        graph = None
        for line in vcg_string:
            if line.startswith("graph: {"):
                json_graph = line.replace("graph: ", "").replace("title", "\"title\"").strip() + "}"
                graph_dict = json.loads(json_graph)
                graph = VCGGraph(graph_dict['title'])
            elif line.startswith("node: {"):
                json_graph = self.format_node(line)
                node_dict = json.loads(json_graph)
                node = VCGNode(node_dict['title'], node_dict['label'], node_dict.get('shape', ''))
                for attr, value in node_dict.items():
                    if attr not in ['title', 'label']:
                        setattr(node, attr[1:], value)
                graph.add_node(node)

            elif line.startswith("edge: {"):
                json_graph = self.format_edge(line)
                edge_dict = json.loads(json_graph)

                edge = VCGEdge(edge_dict['sourcename'], edge_dict['targetname'], edge_dict.get('label', ''))
                for attr, value in edge_dict.items():
                    if attr not in ['sourcename', 'targetname', 'label']:
                        setattr(edge, attr[1:], value)
                graph.add_edge(edge)
        return graph


class VCGGraph(object):
    def __init__(self, title):
        self.title = title
        self.nodes = []
        self.edges = []

    def add_node(self, node):
        self.nodes.append(node)

    def add_edge(self, edge):
        self.edges.append(edge)

    def to_vcg(self):
        vcg_string = 'graph: { title: "%s" \n' % self.title
        for node in self.nodes.values():
            vcg_string += '         node: { title: "%s" label: "%s"' % (node.title, node.label)
            for attr in vars(node):
                if attr not in ['title', 'label']:
                    vcg_string += ' %s: "%s"' % (attr, getattr(node, attr))
            vcg_string += ' }\n'
        for edge in self.edges:
            vcg_string += '         edge: { sourcename: "%s" targetname: "%s" label: "%s"' % (
                edge.sourcename, edge.targetname, edge.label)
            for attr in vars(edge):
                if attr not in ['sourcename', 'targetname', 'label']:
                    vcg_string += ' %s: "%s"' % (attr, getattr(edge, attr))
            vcg_string += ' }\n'
        vcg_string += '       }\n'
        return vcg_string


class VCGNode(object):
    def __init__(self, title, label, shape):
        self.title = title
        self.label = label
        self.shape = shape


class VCGEdge(object):
    def __init__(self, sourcename, targetname, label):
        self.sourcename = sourcename
        self.targetname = targetname
        self.label = label


def beijing_timestamp():
    # 获取当前的UTC时间
    utc_now = datetime.datetime.utcnow()
    # 加上8个小时的偏移量
    beijing_now = utc_now + datetime.timedelta(hours=8)
    # 转换为1970年1月1日以来的秒数
    beijing_timestamp = beijing_now.timestamp()
    # 转换为datetime.datetime对象
    beijing_datetime = datetime.datetime.fromtimestamp(beijing_timestamp)
    # 按照指定的格式输出字符串
    beijing_string = beijing_datetime.strftime("%Y/%m/%d %H:%M:%S")
    # 返回结果
    return beijing_string


# def beijing_timestamp():
#     utc_time = datetime.datetime.utcnow()
#     beijing_tz = datetime.timezone(datetime.timedelta(hours=8))
#     beijing_time = utc_time.astimezone(beijing_tz)
#     return beijing_time.strftime("%Y/%m/%d %H:%M:%S")


def check_python_version():
    current_python = sys.version_info[0]
    if current_python == 3:
        return
    else:
        raise Exception('Invalid python version requested: %d' % current_python)


def process_per_ci(ci_file_with_index):
    (index, total, db_file_path, ci_file_path, logger) = ci_file_with_index

    conn = sqlite3.connect(db_file_path, timeout=120)
    conn.isolation_level = ""
    cursor = conn.cursor()
    conn.execute("PRAGMA journal_mode=WAL")

    try:
        graph = VCGParser().parse_file(ci_file_path)
        logger.debug(f"new ci graph: {graph.title}")
        cursor.execute(f"INSERT INTO KFLOW_GRAPH (GRAPH,PATH) VALUES (?,?) ", (graph.title, ci_file_path))
        for node in graph.nodes:
            cursor.execute(f'INSERT INTO KFLOW_NODE (TITLE,LABEL,SHAPE,GRAPH,PATH)  VALUES (?,?,?,?,?) ',
                           (
                               node.title, node.label, repr(node.shape), graph.title, ci_file_path,
                           )
                           )
            logger.debug(f"node title: {node.title}, label: {repr(node.label)}")
        for edge in graph.edges:
            cursor.execute(f"INSERT INTO KFLOW_EDGE (SOURCENAME,TARGETNAME,LABEL,GRAPH,PATH) VALUES (?,?,?,?,?) ",
                           (
                               edge.sourcename, edge.targetname, repr(edge.label), graph.title, ci_file_path,
                           )
                           )
            logger.debug(f"edge source: {edge.sourcename}, target: {edge.targetname}, label: {repr(edge.label)}")
    except Exception as e:
        logger.error(f"kflow scan error {str(e)} \n error accur when tackle {ci_file_path}")

    conn.commit()
    cursor.close()
    conn.close()
    logger.info(f"[ {index}/{total} ] Dir: {ci_file_path}")


def find_ci_files(dir_path):
    file_list = []
    for entry in os.scandir(dir_path):
        if entry.is_file() and entry.name.endswith(".ci"):
            file_list.append(entry.path)
        elif entry.is_dir():
            file_list.extend(find_ci_files(entry.path))
    return file_list


def handle_scan(args):
    logger = args.logger
    begin_time = beijing_timestamp()
    workdir = os.path.abspath(args.workdir)
    logger.info(f"WORKDIR {workdir}")

    conn = sqlite3.connect(args.output, timeout=120)
    cursor = conn.cursor()

    # 总是删除重建，因为条件插入太慢，sqlite3性能有限，对读与哦好
    cursor.execute("DROP TABLE IF EXISTS KFLOW_GRAPH;")
    cursor.execute("DROP TABLE IF EXISTS KFLOW_NODE;")
    cursor.execute("DROP TABLE IF EXISTS KFLOW_EDGE;")
    conn.commit()

    cursor.execute(
        f"CREATE TABLE IF NOT EXISTS KFLOW_GRAPH ("
        f" ID INTEGER PRIMARY KEY AUTOINCREMENT, "
        f" GRAPH TEXT , "
        f" PATH TEXT"
        f")"
    )
    conn.commit()
    cursor.execute(
        f"CREATE TABLE IF NOT EXISTS KFLOW_NODE ("
        f" ID INTEGER PRIMARY KEY AUTOINCREMENT, "
        f" TITLE TEXT , "
        f" LABEL TEXT , "
        f" SHAPE TEXT , "
        f" GRAPH TEXT , "
        f" PATH TEXT"
        f")"
    )
    conn.commit()
    cursor.execute(
        f"CREATE TABLE IF NOT EXISTS KFLOW_EDGE ("
        f" ID INTEGER PRIMARY KEY AUTOINCREMENT, "
        f" SOURCENAME TEXT , "
        f" TARGETNAME TEXT , "
        f" LABEL TEXT , "
        f" GRAPH TEXT , "
        f" PATH TEXT"
        f")"
    )
    conn.commit()
    cursor.close()
    conn.close()

    logger.info(" scan ...")
    ci_file_list = find_ci_files(workdir)
    ci_file_with_index = []
    total = len(ci_file_list)
    for i, ci in enumerate(ci_file_list):
        ci = os.path.abspath(ci)
        ci_file_with_index.append(
            (i + 1, total, args.output, ci, logger)
        )

    pool = multiprocessing.Pool(args.job)
    pool.imap_unordered(process_per_ci, ci_file_with_index)
    pool.close()
    pool.join()

    end_time = beijing_timestamp()
    logger.info(f"handle kflow scan done! {begin_time} - {end_time}")


def get_sqltable_record_num(cursor, table_name):
    try:
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        count = cursor.fetchone()[0]
        return (True, count)
    except Exception as e:
        return (False, str(e))


def handle_stat(args):
    logger = args.logger
    begin_time = beijing_timestamp()

    workdir = os.path.abspath(args.workdir)
    logger.info(f"WORKDIR {workdir}")

    db_file_path = os.path.abspath(args.output)
    if not os.path.isfile(db_file_path):
        logger.error(f" Database file {db_file_path} not found!")
    logger.info(f"using {db_file_path}")

    conn = sqlite3.connect(args.output, timeout=120)
    cursor = conn.cursor()
    logger.info("-" * 30)

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'KFLOW%'")
    tables = cursor.fetchall()
    for table in tables:
        (status, info) = get_sqltable_record_num(cursor, table[0])
        if status:
            logger.info(f" {table[0]} total: {info} ")
        else:
            logger.info(f" get {table[0]} failed! {info}")

    logger.info("-" * 30)
    cursor.close()
    conn.close()

    end_time = beijing_timestamp()
    print(f"handle kflow stat done! {begin_time} - {end_time}")


def setting_logger(args):
    # 创建一个logger对象
    logger = logging.getLogger("file_logger")
    logger.setLevel(logging.INFO)
    console_handler = logging.StreamHandler()
    # 创建一个handler对象，用于输出到用户指定的日志文件
    file_handler = logging.FileHandler(args.log)
    formatter = logging.Formatter("%(asctime)s - %(levelname)s : %(message)s")
    console_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    return logger


def handle_query(args):
    logger = args.logger
    begin_time = beijing_timestamp()

    workdir = os.path.abspath(args.workdir)
    logger.info(f"WORKDIR {workdir}")

    db_file_path = os.path.abspath(args.output)
    if not os.path.isfile(db_file_path):
        logger.error(f" Database file {db_file_path} not found!")
    logger.info(f"using {db_file_path}")

    conn = sqlite3.connect(args.output, timeout=120)
    cursor = conn.cursor()
    logger.info("-" * 30)

    cursor.execute(f"SELECT * FROM {args.table} LIMIT {args.number}")
    records = cursor.fetchall()

    if len(records) == 0:
        logger.info(f" no record found in {args.table}")
    for record in records:
        column_names = [cursor[0] for cursor in cursor.description]
        record_dict = dict(zip(column_names, record))
        info = ""
        for key, value in record_dict.items():
            info += f"{key}:{repr(value)} "
        logger.info(info)

    logger.info("-" * 30)
    cursor.close()
    conn.close()

    end_time = beijing_timestamp()
    print(f"handle kflow stat done! {begin_time} - {end_time}")


def export_csv(cursor, table_name):
    cursor.execute(f"SELECT * FROM {table_name}")
    data = cursor.fetchall()
    col_names = [description[0] for description in cursor.description]

    with open(f"{table_name}.csv", 'w', encoding='UTF8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(col_names)
        writer.writerows(data)
    return len(data)


def handle_export(args):
    logger = args.logger
    begin_time = beijing_timestamp()

    workdir = os.path.abspath(args.workdir)
    logger.info(f"WORKDIR {workdir}")

    db_file_path = os.path.abspath(args.output)
    if not os.path.isfile(db_file_path):
        logger.error(f" Database file {db_file_path} not found!")
    logger.info(f"using {db_file_path}")

    conn = sqlite3.connect(args.output, timeout=120)
    cursor = conn.cursor()
    logger.info("-" * 30)

    if args.table == "all":
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'KFLOW%'")
        tables = cursor.fetchall()
        for table in tables:
            num = export_csv(cursor, table[0])
            logger.info(f" export {table[0]} done! [{num}]")
    else:
        cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name=?", (args.table))
        result = cursor.fetchone()[0]
        if result:
            num = export_csv(cursor, result)
            logger.info(f" export {result} done! [{num}]")
        else:
            logger.error(f" no table named {result} found!")

    logger.info("-" * 30)
    cursor.close()
    conn.close()

    end_time = beijing_timestamp()
    print(f"handle kflow stat done! {begin_time} - {end_time}")


def main():
    global CURRENT_VERSION
    check_python_version()

    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("-v", "--version", action="store_true",
                        help="show program's version number and exit")
    parser.add_argument("-h", "--help", action="store_true",
                        help="show this help message and exit")

    subparsers = parser.add_subparsers()

    # 定义base命令用于集成
    parent_parser = argparse.ArgumentParser(add_help=False, description="kdev - a tool for kernel development")
    parent_parser.add_argument("-V", "--verbose", default=None, action="store_true", help="show verbose output")
    # job数量不宜太大，sqlite3写入性能有限
    parent_parser.add_argument("-j", "--job", default=os.cpu_count(), type=int, help="job count")
    parent_parser.add_argument("-o", "--output", default="kflow.db", help="kflow database file path")
    parent_parser.add_argument("-w", "--workdir", default=".", help="setup workdir")
    parent_parser.add_argument('-l', '--log', default="kflow.log", help="log file path")
    parent_parser.add_argument('-d', '--debug', default=None, action="store_true", help="enable debug output")

    # 添加子命令 scan
    parser_scan = subparsers.add_parser('scan', parents=[parent_parser])
    parser_scan.set_defaults(func=handle_scan)

    # 添加子命令 stat
    parser_stat = subparsers.add_parser('stat', parents=[parent_parser])
    parser_stat.set_defaults(func=handle_stat)

    # 添加子命令 query
    parser_query = subparsers.add_parser('query', parents=[parent_parser])
    parser_query.add_argument('-t', '--table', default='KFLOW_GRAPH',
                              help="show specific table info, default KFLOW_GRAPH")
    parser_query.add_argument('-n', '--number', default=20, type=int,
                              help="show number record of table")
    parser_query.set_defaults(func=handle_query)

    # 添加子命令 export
    parser_export = subparsers.add_parser('export', parents=[parent_parser])
    parser_export.add_argument('-t', '--table', default='all',
                               help="export specific table (tablename start with KFLOW)")
    parser_export.set_defaults(func=handle_export)

    # 开始解析命令
    args = parser.parse_args()

    if args.version:
        print("kflow %s" % CURRENT_VERSION)
        sys.exit(0)
    elif args.help or len(sys.argv) < 2:
        parser.print_help()
        sys.exit(0)
    else:
        args.logger = setting_logger(args)
        args.func(args)


if __name__ == "__main__":
    main()
