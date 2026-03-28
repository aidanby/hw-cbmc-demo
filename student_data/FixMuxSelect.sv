// 4:1 multiplexer with 2-bit select.
// The multiplexer is routing some inputs to incorrect outputs.
module mux4(input [3:0] d, input [1:0] sel, output reg out);
  always @(*) begin
    case (sel)
      2'b00: out = d[1];
      2'b01: out = d[0];
      2'b10: out = d[2];
      2'b11: out = d[0];
    endcase
  end

  p_sel0: assert final (sel != 2'b00 || out == d[0]);
  p_sel1: assert final (sel != 2'b01 || out == d[1]);
  p_sel2: assert final (sel != 2'b10 || out == d[2]);
  p_sel3: assert final (sel != 2'b11 || out == d[3]);
endmodule
