// 2-client round-robin arbiter.
// BUG: arbiter always grants client 0, ignoring the turn register.
// Fix the fairness logic so all properties pass.
module arbiter_fair(input clk, input reset,
                    input req0, req1,
                    output reg grant0, output reg grant1);
  reg turn;  // 0 = prefer client 0, 1 = prefer client 1
  initial begin
    grant0 = 0;
    grant1 = 0;
    turn   = 0;
  end

  always @(posedge clk) begin
    if (reset) begin
      grant0 <= 0;
      grant1 <= 0;
      turn   <= 0;
    end else begin
      grant0 <= 0;
      grant1 <= 0;
      // BUG: always grants client 0 if it requests, ignoring turn
      if (req0) begin        // BUG: should check turn or give client1 fair chance
        grant0 <= 1;
        turn   <= 1;
      end else if (req1) begin
        grant1 <= 1;
        turn   <= 0;
      end
    end
  end

  p_mutex:  assert property (@(posedge clk) !(grant0 && grant1));
  p_fair0:  assert property (@(posedge clk) req0 && req1 && turn == 1 |=> grant1);
  p_fair1:  assert property (@(posedge clk) req0 && req1 && turn == 0 |=> grant0);
endmodule
