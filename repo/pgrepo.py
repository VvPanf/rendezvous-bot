import psycopg2 as pg

class PgRepo:
    def __init__(self, db_url):
        self.db_url = db_url
        with self.__get_conn() as con:
            with con.cursor() as cur:
                with open('./sql/create.sql', 'r') as file:
                    cur.execute(file.read())

    def __get_conn(self):
        return pg.connect(self.db_url)

    def __make_user(self, res):
        return {
            "id": res[0],
            "user_id": res[1],
            "state": res[2]
        }

    def __make_rendezvous(self, res):
        return {
            "id": res[0],
            "first": res[1],
            "second": res[2],
            "plan": res[3],
            "stage_count": res[4],
            "current_stage": res[5]
        }

    def find_user(self, user):
        with self.__get_conn() as con:
            with con.cursor() as cur:
                cur.execute("select id, user_id, state from users where user_id=%s", (user,))
                res = cur.fetchone()
                return self.__make_user(res) if res is not None else None

    def save_user(self, user):
        with self.__get_conn() as con:
            with con.cursor() as cur:
                cur.execute("insert into users(user_id) values (%s)", (user,))
                con.commit()

    def save_user_state(self, user, state):
        with self.__get_conn() as con:
            with con.cursor() as cur:
                cur.execute("update users set state=%s where user_id=%s", (state, user,))
                con.commit()

    def find_rendezvous_by_first(self, user):
        with self.__get_conn() as con:
            with con.cursor() as cur:
                cur.execute("""
                    select r.id, u1.user_id, u2.user_id, plan, stage_count, current_stage  
                    from rendezvous r join users u1 on r.first_person = u1.id
                    join users u2 on r.second_person = u2.id
                    where u1.user_id = %s
                    """, (user,))
                res = cur.fetchone()
                return self.__make_rendezvous(res) if res is not None else None

    def find_rendezvous_by_second(self, user):
        with self.__get_conn() as con:
            with con.cursor() as cur:
                cur.execute("""
                    select r.id, u1.user_id, u2.user_id, plan, stage_count, current_stage  
                    from rendezvous r join users u1 on r.first_person = u1.id
                    join users u2 on r.second_person = u2.id
                    where u2.user_id = %s
                    """, (user,))
                res = cur.fetchone()
                return self.__make_rendezvous(res) if res is not None else None

    def save_new_rendezvous(self, first, second):
        with self.__get_conn() as con:
            with con.cursor() as cur:
                cur.execute("insert into rendezvous(first_person, second_person) values (%s,%s)", (first, second,))
                con.commit()

    def save_rendezvous_plan(self, user, plan, stage_count, current_stage):
        with self.__get_conn() as con:
            with con.cursor() as cur:
                cur.execute("update rendezvous set plan=%s, stage_count=%s, current_stage=%s where first_person=%s",
                            (plan, stage_count, current_stage, user,))
                con.commit()

    def save_rendezvous_current_stage(self, user, current_stage):
        with self.__get_conn() as con:
            with con.cursor() as cur:
                cur.execute("update rendezvous set current_stage=%s where first_person=%s",
                            (current_stage, user,))
                con.commit()

    def delete_rendezvous(self, user):
        with self.__get_conn() as con:
            with con.cursor() as cur:
                cur.execute("delete from rendezvous where first_person=%s",
                            (user,))
                con.commit()
