from models import get_db


def create(color_id, file_path, loai_anh, user_id, ghi_chu=""):
    db = get_db()
    cur = db.execute(
        """INSERT INTO color_images (color_id, file_path, loai_anh, uploaded_by, ghi_chu)
           VALUES (%s,%s,%s,%s,%s) RETURNING id""",
        (color_id, file_path, loai_anh, user_id, ghi_chu),
    )
    image_id = cur.fetchone()["id"]
    db.commit()
    return image_id


def list_for_color(color_id):
    return get_db().execute(
        """SELECT i.*, u.username FROM color_images i
           LEFT JOIN users u ON u.id = i.uploaded_by
           WHERE i.color_id = %s ORDER BY i.id DESC""",
        (color_id,),
    ).fetchall()


def get(image_id):
    return get_db().execute("SELECT * FROM color_images WHERE id = %s", (image_id,)).fetchone()


def delete(image_id):
    db = get_db()
    db.execute("DELETE FROM color_images WHERE id = %s", (image_id,))
    db.commit()