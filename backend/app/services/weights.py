"""Share redistribution. Pinned weights stay; the rest split the remainder to 100."""


class ShareError(Exception):
    """Pinned shares leave no valid way to make active shares sum to 100."""


def redistribute_shares(
    items: list[dict],
    *,
    share_key: str = "share",
    pinned_key: str = "is_pinned",
    status_key: str = "status",
    active_status: str = "active",
) -> list[dict]:
    """
    Active shares sum to 100 when there is at least one active offer.
    Pinned offers keep the share the caller set. Unpinned offers split what is left.
    Raises ShareError instead of shrinking pins or giving an offer 0%.
    """
    active = [i for i in items if i.get(status_key, active_status) == active_status]
    removed = [i for i in items if i.get(status_key, active_status) != active_status]

    for item in removed:
        item[share_key] = 0

    if not active:
        return items

    pinned = [i for i in active if i.get(pinned_key)]
    free = [i for i in active if not i.get(pinned_key)]
    pinned_total = sum(int(i.get(share_key) or 0) for i in pinned)

    if pinned_total > 100 or (not free and pinned_total != 100) or (free and pinned_total >= 100):
        raise ShareError(
            "Закреплённые доли не оставляют сумму 100%. "
            "Уменьшите pin или снимите его, прежде чем добавлять оффер."
        )

    if not free:
        return items

    remainder = 100 - pinned_total
    base = remainder // len(free)
    extra = remainder % len(free)
    for idx, item in enumerate(free):
        item[share_key] = base + (1 if idx < extra else 0)

    return items
