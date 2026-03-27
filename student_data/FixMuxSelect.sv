// 4:1 multiplexer with 2-bit select.
// BUG: select bits are indexed in wrong order — sel[0] used as MSB, sel[1] as LSB.
// Fix the select indexing so all properties pass.
module mux4(input [3:0] d, input [1:0] sel, output reg out);
  always @(*) begin
    // BUG: should be case (sel) but bits are reversed in the case expression
    case ({sel[0], sel[1]})   // BUG: should be case (sel) i.e. {sel[1], sel[0]}
      2'b00: out = d[0];
      2'b01: out = d[1];
      2'b10: out = d[2];
      2'b11: out = d[3];
    endcase
  end

  p_sel1: assert final (sel != 2'b01 || out == d[1]);
  p_sel2: assert final (sel != 2'b10 || out == d[2]);
endmodule
