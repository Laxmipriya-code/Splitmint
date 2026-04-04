from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from sqlalchemy import func, select

from app.core.security import hash_password
from app.db.models import Expense, ExpenseSplit, Group, Participant, User
from app.db.session import get_session_factory
from app.schemas.expense import ExpenseSplitValueInput, ExpenseUpsertRequest
from app.schemas.group import GroupCreateRequest
from app.schemas.participant import ParticipantCreateRequest
from app.services.expenses import expense_service
from app.services.groups import group_service
from app.services.participants import participant_service


def money(value: str) -> Decimal:
    return Decimal(value)


@dataclass(frozen=True, slots=True)
class ParticipantSeed:
    alias: str
    name: str


@dataclass(frozen=True, slots=True)
class ExpenseSeed:
    description: str
    amount: str
    category: str
    date: str
    payer_alias: str
    participant_aliases: tuple[str, ...]
    split_mode: str
    split_values: tuple[tuple[str, str], ...] = ()
    expected_owed_amounts: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class BalanceExpectation:
    alias: str
    net_balance: str
    is_active: bool = True


@dataclass(frozen=True, slots=True)
class SettlementExpectation:
    from_alias: str
    to_alias: str
    amount: str


@dataclass(frozen=True, slots=True)
class GroupSeed:
    name: str
    participants: tuple[ParticipantSeed, ...]
    expenses: tuple[ExpenseSeed, ...]
    deactivated_aliases: tuple[str, ...]
    expected_total_spent: str
    expected_balances: tuple[BalanceExpectation, ...]
    expected_settlements: tuple[SettlementExpectation, ...]


@dataclass(frozen=True, slots=True)
class UserSeed:
    email: str
    display_name: str
    password: str
    groups: tuple[GroupSeed, ...] = field(default_factory=tuple)


SEED_USERS: tuple[UserSeed, ...] = (
    UserSeed(
        email="demo.amit@example.com",
        display_name="Amit Mehra",
        password="SeedPass123!",
        groups=(
            GroupSeed(
                name="Goa Friends Trip",
                participants=(
                    ParticipantSeed(alias="riya", name="Riya Kapoor"),
                    ParticipantSeed(alias="karan", name="Karan Shah"),
                    ParticipantSeed(alias="sara", name="Sara Dsouza"),
                ),
                expenses=(
                    ExpenseSeed(
                        description="Airport taxi from Dabolim",
                        amount="89.95",
                        category="Transport",
                        date="2026-03-26",
                        payer_alias="owner",
                        participant_aliases=("owner", "riya", "karan", "sara"),
                        split_mode="equal",
                        expected_owed_amounts=("22.48", "22.49", "22.49", "22.49"),
                    ),
                    ExpenseSeed(
                        description="Villa booking deposit",
                        amount="321.55",
                        category="Lodging",
                        date="2026-03-26",
                        payer_alias="riya",
                        participant_aliases=("owner", "riya", "karan", "sara"),
                        split_mode="percentage",
                        split_values=(
                            ("owner", "40.0000"),
                            ("riya", "30.0000"),
                            ("karan", "20.0000"),
                            ("sara", "10.0000"),
                        ),
                        expected_owed_amounts=("128.62", "96.46", "64.31", "32.16"),
                    ),
                    ExpenseSeed(
                        description="Scooter fuel and parking",
                        amount="73.50",
                        category="Transport",
                        date="2026-03-27",
                        payer_alias="karan",
                        participant_aliases=("owner", "karan", "sara"),
                        split_mode="custom",
                        split_values=(
                            ("owner", "18.50"),
                            ("karan", "30.00"),
                            ("sara", "25.00"),
                        ),
                        expected_owed_amounts=("18.50", "30.00", "25.00"),
                    ),
                    ExpenseSeed(
                        description="Seafood dinner at Calangute",
                        amount="212.40",
                        category="Food",
                        date="2026-03-28",
                        payer_alias="sara",
                        participant_aliases=("owner", "riya", "karan", "sara"),
                        split_mode="equal",
                        expected_owed_amounts=("53.10", "53.10", "53.10", "53.10"),
                    ),
                    ExpenseSeed(
                        description="Checkout breakfast",
                        amount="96.00",
                        category="Food",
                        date="2026-03-29",
                        payer_alias="owner",
                        participant_aliases=("owner", "riya", "sara"),
                        split_mode="equal",
                        expected_owed_amounts=("32.00", "32.00", "32.00"),
                    ),
                ),
                deactivated_aliases=("karan",),
                expected_total_spent="793.40",
                expected_balances=(
                    BalanceExpectation(alias="owner", net_balance="-68.75"),
                    BalanceExpectation(alias="riya", net_balance="117.50"),
                    BalanceExpectation(alias="karan", net_balance="-96.40", is_active=False),
                    BalanceExpectation(alias="sara", net_balance="47.65"),
                ),
                expected_settlements=(
                    SettlementExpectation(from_alias="karan", to_alias="riya", amount="96.40"),
                    SettlementExpectation(from_alias="owner", to_alias="riya", amount="21.10"),
                    SettlementExpectation(from_alias="owner", to_alias="sara", amount="47.65"),
                ),
            ),
        ),
    ),
    UserSeed(
        email="demo.nisha@example.com",
        display_name="Nisha Iyer",
        password="SeedPass123!",
        groups=(
            GroupSeed(
                name="Flat 4B Monthly Expenses",
                participants=(
                    ParticipantSeed(alias="dev", name="Dev Malhotra"),
                    ParticipantSeed(alias="mehul", name="Mehul Jain"),
                ),
                expenses=(
                    ExpenseSeed(
                        description="Electricity bill - March",
                        amount="146.70",
                        category="Utilities",
                        date="2026-03-30",
                        payer_alias="owner",
                        participant_aliases=("owner", "dev", "mehul"),
                        split_mode="equal",
                        expected_owed_amounts=("48.90", "48.90", "48.90"),
                    ),
                    ExpenseSeed(
                        description="Groceries from FreshMart",
                        amount="238.45",
                        category="Groceries",
                        date="2026-03-31",
                        payer_alias="dev",
                        participant_aliases=("owner", "dev", "mehul"),
                        split_mode="custom",
                        split_values=(
                            ("owner", "90.15"),
                            ("dev", "88.15"),
                            ("mehul", "60.15"),
                        ),
                        expected_owed_amounts=("90.15", "88.15", "60.15"),
                    ),
                    ExpenseSeed(
                        description="Internet recharge",
                        amount="89.99",
                        category="Internet",
                        date="2026-04-01",
                        payer_alias="mehul",
                        participant_aliases=("owner", "dev", "mehul"),
                        split_mode="percentage",
                        split_values=(
                            ("owner", "50.0000"),
                            ("dev", "25.0000"),
                            ("mehul", "25.0000"),
                        ),
                        expected_owed_amounts=("44.99", "22.50", "22.50"),
                    ),
                    ExpenseSeed(
                        description="Household cleaning supplies",
                        amount="54.80",
                        category="Supplies",
                        date="2026-04-02",
                        payer_alias="owner",
                        participant_aliases=("owner", "dev"),
                        split_mode="equal",
                        expected_owed_amounts=("27.40", "27.40"),
                    ),
                ),
                deactivated_aliases=(),
                expected_total_spent="529.94",
                expected_balances=(
                    BalanceExpectation(alias="owner", net_balance="-9.94"),
                    BalanceExpectation(alias="dev", net_balance="51.50"),
                    BalanceExpectation(alias="mehul", net_balance="-41.56"),
                ),
                expected_settlements=(
                    SettlementExpectation(from_alias="mehul", to_alias="dev", amount="41.56"),
                    SettlementExpectation(from_alias="owner", to_alias="dev", amount="9.94"),
                ),
            ),
        ),
    ),
)

SEED_EMAILS = tuple(user.email for user in SEED_USERS)


def assert_decimal(actual: Decimal, expected: str, *, context: str) -> None:
    expected_decimal = money(expected)
    if actual != expected_decimal:
        raise AssertionError(f"{context}: expected {expected_decimal} but found {actual}")


def purge_existing_demo_users(db) -> None:
    existing = db.execute(select(User).where(User.email.in_(SEED_EMAILS))).scalars().all()
    for user in existing:
        db.delete(user)
    db.commit()


def create_user(db, seed: UserSeed) -> User:
    user = User(
        email=seed.email,
        display_name=seed.display_name,
        password_hash=hash_password(seed.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def build_expense_payload(
    *,
    group_id,
    participant_ids: dict[str, object],
    expense_seed: ExpenseSeed,
) -> ExpenseUpsertRequest:
    split_values = [
        ExpenseSplitValueInput(
            participant_id=participant_ids[alias],
            value=money(value),
        )
        for alias, value in expense_seed.split_values
    ]
    return ExpenseUpsertRequest(
        group_id=group_id,
        amount=money(expense_seed.amount),
        description=expense_seed.description,
        category=expense_seed.category,
        date=date.fromisoformat(expense_seed.date),
        payer_id=participant_ids[expense_seed.payer_alias],
        participants=[participant_ids[alias] for alias in expense_seed.participant_aliases],
        split_mode=expense_seed.split_mode,
        splits=split_values,
    )


def validate_expense(expense, expense_seed: ExpenseSeed, *, context: str) -> None:
    assert_decimal(expense.amount, expense_seed.amount, context=f"{context} amount")
    if not expense_seed.expected_owed_amounts:
        return
    actual_owed = tuple(str(split.owed_amount) for split in expense.splits)
    if actual_owed != expense_seed.expected_owed_amounts:
        raise AssertionError(
            f"{context} owed amounts: expected {expense_seed.expected_owed_amounts} "
            f"but found {actual_owed}"
        )


def validate_snapshot(snapshot, *, name_by_alias: dict[str, str], group_seed: GroupSeed) -> None:
    assert_decimal(snapshot.total_spent, group_seed.expected_total_spent, context=group_seed.name)

    balances_by_name = {balance.name: balance for balance in snapshot.balances}
    for expectation in group_seed.expected_balances:
        participant_name = name_by_alias[expectation.alias]
        balance = balances_by_name[participant_name]
        assert_decimal(
            balance.net_balance,
            expectation.net_balance,
            context=f"{group_seed.name} net balance for {participant_name}",
        )
        if balance.is_active is not expectation.is_active:
            raise AssertionError(
                f"{group_seed.name} active flag for {participant_name}: expected "
                f"{expectation.is_active} but found {balance.is_active}"
            )

    owner_net = next(
        money(expectation.net_balance)
        for expectation in group_seed.expected_balances
        if expectation.alias == "owner"
    )
    if owner_net < Decimal("0.00"):
        assert_decimal(
            snapshot.you_owe,
            str(abs(owner_net)),
            context=f"{group_seed.name} owner you_owe",
        )
        assert_decimal(
            snapshot.you_are_owed,
            "0.00",
            context=f"{group_seed.name} owner you_are_owed",
        )
    else:
        assert_decimal(
            snapshot.you_owe,
            "0.00",
            context=f"{group_seed.name} owner you_owe",
        )
        assert_decimal(
            snapshot.you_are_owed,
            str(owner_net),
            context=f"{group_seed.name} owner you_are_owed",
        )

    actual_settlements = tuple(
        (settlement.from_name, settlement.to_name, str(settlement.amount))
        for settlement in snapshot.settlements
    )
    expected_settlements = tuple(
        (
            name_by_alias[settlement.from_alias],
            name_by_alias[settlement.to_alias],
            settlement.amount,
        )
        for settlement in group_seed.expected_settlements
    )
    if actual_settlements != expected_settlements:
        raise AssertionError(
            f"{group_seed.name} settlements: expected {expected_settlements} "
            f"but found {actual_settlements}"
        )


def seed_group(db, *, owner: User, group_seed: GroupSeed) -> None:
    group = group_service.create_group(db, owner, GroupCreateRequest(name=group_seed.name))

    participant_ids = {"owner": group.owner_participant_id}
    name_by_alias = {"owner": owner.display_name or owner.email.split("@", 1)[0]}

    for participant_seed in group_seed.participants:
        participant = participant_service.add_participant(
            db,
            owner,
            group.id,
            ParticipantCreateRequest(name=participant_seed.name),
        )
        participant_ids[participant_seed.alias] = participant.id
        name_by_alias[participant_seed.alias] = participant.name

    for index, expense_seed in enumerate(group_seed.expenses, start=1):
        payload = build_expense_payload(
            group_id=group.id,
            participant_ids=participant_ids,
            expense_seed=expense_seed,
        )
        expense = expense_service.create_expense(db, owner, payload)
        validate_expense(
            expense,
            expense_seed,
            context=f"{group_seed.name} expense #{index} ({expense_seed.description})",
        )

    for alias in group_seed.deactivated_aliases:
        participant_service.remove_participant(db, owner, participant_ids[alias])

    snapshot = group_service.get_balance_snapshot(db, owner, group.id)
    validate_snapshot(snapshot, name_by_alias=name_by_alias, group_seed=group_seed)

    print(f"Seeded group: {group_seed.name}")
    print(f"  owner: {owner.display_name} <{owner.email}>")
    print(f"  total spent: {snapshot.total_spent}")
    for balance in snapshot.balances:
        status = "active" if balance.is_active else "inactive"
        owner_flag = " owner" if balance.is_owner else ""
        print(
            f"  - {balance.name}: paid={balance.paid_total} owed={balance.owed_total} "
            f"net={balance.net_balance} [{status}{owner_flag}]"
        )
    for settlement in snapshot.settlements:
        print(f"    settlement: {settlement.from_name} -> {settlement.to_name} = {settlement.amount}")


def print_table_counts(db) -> None:
    tables = (
        ("users", User),
        ("groups", Group),
        ("participants", Participant),
        ("expenses", Expense),
        ("expense_splits", ExpenseSplit),
    )
    print("Final row counts:")
    for label, model in tables:
        count = db.execute(select(func.count()).select_from(model)).scalar_one()
        print(f"  {label}: {count}")


def main() -> None:
    session_factory = get_session_factory()
    with session_factory() as db:
        try:
            purge_existing_demo_users(db)
            for user_seed in SEED_USERS:
                user = create_user(db, user_seed)
                for group_seed in user_seed.groups:
                    seed_group(db, owner=user, group_seed=group_seed)
            print_table_counts(db)
        except Exception:
            db.rollback()
            raise


if __name__ == "__main__":
    main()
