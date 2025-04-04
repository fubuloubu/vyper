import pytest

from vyper.evm.opcodes import version_check


@pytest.mark.parametrize("location", ["storage", "transient"])
def test_extract32_extraction(tx_failed, get_contract, location):
    if location == "transient" and not version_check(begin="cancun"):
        pytest.skip(
            "Skipping test as storage_location is 'transient' and EVM version is pre-Cancun"
        )
    if location == "storage":
        decl = "y: Bytes[100]"
    elif location == "transient":
        decl = "y: transient(Bytes[100])"
    else:
        raise Exception("unreachable")
    extract32_code = f"""
{decl}
@external
def extrakt32(inp: Bytes[100], index: uint256) -> bytes32:
    return extract32(inp, index)

@external
def extrakt32_mem(inp: Bytes[100], index: uint256) -> bytes32:
    x: Bytes[100] = inp
    return extract32(x, index)

@external
def extrakt32_storage(index: uint256, inp: Bytes[100]) -> bytes32:
    self.y = inp
    return extract32(self.y, index)
    """

    c = get_contract(extract32_code)
    test_cases = (
        (b"c" * 31, 0),
        (b"c" * 32, 0),
        (b"c" * 33, 0),
        (b"c" * 33, 1),
        (b"c" * 33, 2),
        (b"cow" * 30, 0),
        (b"cow" * 30, 1),
        (b"cow" * 30, 31),
        (b"cow" * 30, 32),
        (b"cow" * 30, 33),
        (b"cow" * 30, 34),
        (b"cow" * 30, 58),
        (b"cow" * 30, 59),
    )

    for S, i in test_cases:
        if 0 <= i <= len(S) - 32:
            expected_result = S[i : i + 32]
            assert c.extrakt32(S, i) == expected_result
            assert c.extrakt32_mem(S, i) == expected_result
            assert c.extrakt32_storage(i, S) == expected_result
        else:
            with tx_failed():
                c.extrakt32(S, i)


def test_extract32_code(tx_failed, get_contract):
    extract32_code = """
@external
def foo(inp: Bytes[32]) -> int128:
    return extract32(inp, 0, output_type=int128)

@external
def bar(inp: Bytes[32]) -> uint256:
    return extract32(inp, 0, output_type=uint256)

@external
def baz(inp: Bytes[32]) -> bytes32:
    return extract32(inp, 0, output_type=bytes32)

@external
def fop(inp: Bytes[32]) -> bytes32:
    return extract32(inp, 0)

@external
def foq(inp: Bytes[32]) -> address:
    return extract32(inp, 0, output_type=address)
    """

    c = get_contract(extract32_code)
    assert c.foo(b"\x00" * 30 + b"\x01\x01") == 257
    assert c.bar(b"\x00" * 30 + b"\x01\x01") == 257

    with tx_failed():
        c.foo(b"\x80" + b"\x00" * 30)

    assert c.bar(b"\x80" + b"\x00" * 31) == 2**255

    assert c.baz(b"crow" * 8) == b"crow" * 8
    assert c.fop(b"crow" * 8) == b"crow" * 8
    assert c.foq(b"\x00" * 12 + b"3" * 20) == "0x" + "3" * 40

    with tx_failed():
        c.foq(b"crow" * 8)


def test_extract32_order_of_eval(get_contract):
    extract32_code = """
var:DynArray[Bytes[96], 1]

@internal
def bar() -> uint256:
    self.var[0] = b'hellohellohellohellohellohellohello'
    self.var.pop()
    return 3

@external
def foo() -> bytes32:
    self.var = [b'abcdefghijklmnopqrstuvwxyz123456789']
    return extract32(self.var[0], self.bar(), output_type=bytes32)
    """

    c = get_contract(extract32_code)
    assert c.foo() == b"defghijklmnopqrstuvwxyz123456789"


def test_extract32_order_of_eval_extcall(get_contract):
    slice_code = """
var:DynArray[Bytes[96], 1]

interface Bar:
    def bar() -> uint256: payable

@external
def bar() -> uint256:
    self.var[0] = b'hellohellohellohellohellohellohello'
    self.var.pop()
    return 3

@external
def foo() -> bytes32:
    self.var = [b'abcdefghijklmnopqrstuvwxyz123456789']
    return extract32(self.var[0], extcall Bar(self).bar(), output_type=bytes32)
    """

    c = get_contract(slice_code)
    assert c.foo() == b"defghijklmnopqrstuvwxyz123456789"
